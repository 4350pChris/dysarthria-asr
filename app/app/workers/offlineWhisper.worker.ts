import { ModelManager, WhisperWasmService } from '@timur00kh/whisper.wasm'

type WorkerMessage
  = | { type: 'prepare' }
    | { type: 'transcribe', id: number, audio: ArrayBuffer }

type WhisperRuntime = {
  instance: number | null
  wasmModule: {
    full_default: (
      instance: number,
      audio: Float32Array,
      language: string,
      threads: number,
      translate: boolean
    ) => string
  } | null
}

const modelId = 'base-q5_1'
let whisper: WhisperWasmService | undefined

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  if (event.data.type === 'prepare') void prepare()
  if (event.data.type === 'transcribe') void transcribe(event.data)
}

async function prepare() {
  try {
    postMessage({ type: 'status', status: 'loading' })
    const models = new ModelManager({ logLevel: 3 })
    const model = await models.loadModel(modelId, true, (progress) => {
      postMessage({ type: 'progress', progress })
    })
    whisper = new WhisperWasmService({ logLevel: 3 })
    await whisper.initModel(model)
    postMessage({ type: 'ready', modelId })
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
    const runtime = whisper as unknown as WhisperRuntime
    if (!runtime.wasmModule || runtime.instance === null) throw new Error('Offline model is not ready.')
    const text = runtime.wasmModule.full_default(
      runtime.instance,
      new Float32Array(audio),
      'de',
      1,
      false
    ).trim()
    postMessage({ type: 'result', id, text })
  } catch (error) {
    postMessage({ type: 'error', id, message: messageFor(error) })
  }
}

function messageFor(error: unknown) {
  return error instanceof Error ? error.message : 'Offline transcription failed.'
}
