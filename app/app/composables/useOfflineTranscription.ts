import { convertFromFile } from '@timur00kh/whisper.wasm'

type OfflineState = 'idle' | 'loading' | 'ready' | 'failed'

type PendingTranscription = {
  reject: (reason?: unknown) => void
  resolve: (text: string) => void
}

let worker: Worker | undefined
let nextRequestId = 1
const pending = new Map<number, PendingTranscription>()

export function useOfflineTranscription() {
  const modelVersion = useRuntimeConfig().public.offlineWhisperModelVersion
  const modelUrl = modelVersion ? `/offline-whisper-model/${modelVersion}` : ''
  const state = useState<OfflineState>('offline-transcription-state', () => 'idle')
  const error = useState('offline-transcription-error', () => '')

  async function prepare() {
    if (state.value === 'loading' || state.value === 'ready') return
    if (!modelUrl) {
      error.value = 'Für die Offline-Erkennung ist noch kein angepasstes Modell veröffentlicht.'
      state.value = 'failed'
      return
    }
    if (typeof Worker === 'undefined' || typeof AudioContext === 'undefined') {
      error.value = 'Dieses Gerät unterstützt die Offline-Erkennung nicht.'
      state.value = 'failed'
      return
    }
    state.value = 'loading'
    error.value = ''
    getWorker(state, error).postMessage({ type: 'prepare', modelUrl })
  }

  async function transcribe(recording: Blob) {
    if (state.value === 'loading') {
      await new Promise<void>((resolve) => {
        const stop = watch(state, (value) => {
          if (value === 'loading') return
          stop()
          resolve()
        })
      })
    }
    if (state.value !== 'ready') {
      throw new Error(error.value || 'Offline-Erkennung ist nicht bereit.')
    }
    const file = new File([recording], 'recording.webm', { type: recording.type || 'audio/webm' })
    const { audioData } = await convertFromFile(file, {
      normalize: true,
      targetChannels: 1,
      targetSampleRate: 16_000
    })
    const id = nextRequestId++
    const response = new Promise<string>((resolve, reject) => pending.set(id, { resolve, reject }))
    getWorker(state, error).postMessage({
      type: 'transcribe',
      id,
      audio: audioData.buffer
    }, [audioData.buffer])
    return response
  }

  return { error, prepare, state, transcribe }
}

function getWorker(
  state: Ref<OfflineState>,
  error: Ref<string>
) {
  if (worker) return worker
  worker = new Worker(new URL('../workers/offlineWhisper.worker.ts', import.meta.url), { type: 'module' })
  worker.onmessage = (event: MessageEvent<{
    id?: number
    message?: string
    text?: string
    type: 'error' | 'ready' | 'result'
  }>) => {
    const message = event.data
    if (message.type === 'ready') {
      state.value = 'ready'
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
        fail(message.message ?? 'Offline-Erkennung fehlgeschlagen.')
      }
    }
  }
  function fail(message: string) {
    error.value = message
    state.value = 'failed'
    for (const request of pending.values()) request.reject(new Error(message))
    pending.clear()
    worker?.terminate()
    worker = undefined
  }
  worker.onerror = event => fail(event.message || 'Offline-Erkennung konnte nicht gestartet werden.')
  worker.onmessageerror = () => fail('Offline-Erkennung konnte die Audiodaten nicht verarbeiten.')
  return worker
}
