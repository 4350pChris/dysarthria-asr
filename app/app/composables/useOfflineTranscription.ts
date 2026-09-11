type OfflineState = 'idle' | 'loading' | 'ready' | 'failed'

type PendingTranscription = {
  reject: (reason?: unknown) => void
  resolve: (text: string) => void
}

let worker: Worker | undefined
let nextRequestId = 1
const pending = new Map<number, PendingTranscription>()

export function useOfflineTranscription() {
  const modelUrl = useRuntimeConfig().public.offlineWhisperModelUrl
  const state = useState<OfflineState>('offline-transcription-state', () => 'idle')
  const progress = useState('offline-transcription-progress', () => 0)
  const error = useState('offline-transcription-error', () => '')
  const isConfigured = computed(() => Boolean(modelUrl))
  const isReady = computed(() => state.value === 'ready')
  const isSupported = computed(() => typeof Worker !== 'undefined' && typeof AudioContext !== 'undefined')

  async function prepare() {
    if (state.value === 'loading' || state.value === 'ready') return
    if (!isConfigured.value) {
      error.value = 'Für die Offline-Erkennung ist noch kein angepasstes Modell veröffentlicht.'
      state.value = 'failed'
      return
    }
    if (!isSupported.value) {
      error.value = 'Dieses Gerät unterstützt die Offline-Erkennung nicht.'
      state.value = 'failed'
      return
    }
    state.value = 'loading'
    progress.value = 0
    error.value = ''
    getWorker(state, progress, error).postMessage({ type: 'prepare', modelUrl })
  }

  async function transcribe(recording: Blob) {
    if (!isReady.value) throw new Error('Offline-Erkennung ist nicht bereit.')
    const { convertFromFile } = await import('@timur00kh/whisper.wasm')
    const file = new File([recording], 'recording.webm', { type: recording.type || 'audio/webm' })
    const { audioData } = await convertFromFile(file, {
      normalize: true,
      targetChannels: 1,
      targetSampleRate: 16_000
    })
    const id = nextRequestId++
    const response = new Promise<string>((resolve, reject) => pending.set(id, { resolve, reject }))
    getWorker(state, progress, error).postMessage({
      type: 'transcribe',
      id,
      audio: audioData.buffer
    }, [audioData.buffer])
    return response
  }

  return { error, isConfigured, isReady, isSupported, prepare, progress, state, transcribe }
}

function getWorker(
  state: Ref<OfflineState>,
  progress: Ref<number>,
  error: Ref<string>
) {
  if (worker) return worker
  worker = new Worker(new URL('../workers/offlineWhisper.worker.ts', import.meta.url), { type: 'module' })
  worker.onmessage = (event: MessageEvent<{
    id?: number
    message?: string
    progress?: number
    text?: string
    type: 'error' | 'progress' | 'ready' | 'result' | 'status'
  }>) => {
    const message = event.data
    if (message.type === 'progress') progress.value = message.progress ?? 0
    if (message.type === 'ready') {
      state.value = 'ready'
      progress.value = 100
    }
    if (message.type === 'result' && message.id !== undefined) {
      pending.get(message.id)?.resolve(message.text ?? '')
      pending.delete(message.id)
    }
    if (message.type === 'error') {
      error.value = message.message ?? 'Offline-Erkennung fehlgeschlagen.'
      if (message.id !== undefined) {
        pending.get(message.id)?.reject(new Error(error.value))
        pending.delete(message.id)
      } else {
        state.value = 'failed'
      }
    }
  }
  worker.onerror = () => {
    error.value = 'Offline-Erkennung konnte nicht gestartet werden.'
    state.value = 'failed'
  }
  return worker
}
