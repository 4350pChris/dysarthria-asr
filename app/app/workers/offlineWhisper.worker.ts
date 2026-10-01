import { ModelManager, WhisperWasmService } from '@timur00kh/whisper.wasm'

type WorkerMessage
  = | { type: 'prepare', modelUrl: string }
    | { type: 'transcribe', id: number, audio: ArrayBuffer }

let whisper: WhisperWasmService | undefined
const transcriptionOptions = {
  language: 'de',
  threads: Math.min(4, navigator.hardwareConcurrency || 1),
  translate: false
}

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  if (event.data.type === 'prepare') void prepare(event.data.modelUrl)
  if (event.data.type === 'transcribe') void transcribe(event.data)
}

async function prepare(modelUrl: string) {
  try {
    const models = new ModelManager({ logLevel: 3 })
    const model = await models.loadModelByUrl(modelUrl)
    whisper = new WhisperWasmService({ logLevel: 3 })
    await whisper.initModel(model)
    // Start the WASM thread while online so recording needs no worker download.
    await whisper.transcribe(new Float32Array(16_000), undefined, transcriptionOptions)
    postMessage({ type: 'ready' })
  } catch (error) {
    postMessage({ type: 'error', message: messageFor(error) })
  }
}

async function transcribe({ id, audio }: Extract<WorkerMessage, { type: 'transcribe' }>) {
  if (!whisper) {
    postMessage({ type: 'error', id, message: 'Offline model is not ready.' })
    return
  }

  try {
    const audioSamples = new Float32Array(audio)
    if (!audioSamples.length || audioSamples.some(sample => !Number.isFinite(sample))) {
      throw new Error('Offline audio data is empty or invalid.')
    }
    const { segments } = await whisper.transcribe(audioSamples, undefined, transcriptionOptions)
    const text = segments.map(segment => segment.text).join(' ').trim()
    postMessage({ type: 'result', id, text })
  } catch (error) {
    postMessage({ type: 'error', id, message: messageFor(error) })
  }
}

function messageFor(error: unknown) {
  return error instanceof Error ? error.message : 'Offline transcription failed.'
}
