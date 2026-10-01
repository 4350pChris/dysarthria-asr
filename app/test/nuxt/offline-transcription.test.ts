import { expect, it, vi } from 'vitest'
import { defineComponent, h, onMounted } from 'vue'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { checkBackendAvailable } from '~/utils/backendAvailable'
import { useOfflineTranscription } from '~/composables/useOfflineTranscription'

const { initModel, transcribeModel } = vi.hoisted(() => ({
  initModel: vi.fn(async () => {}),
  transcribeModel: vi.fn(async () => ({ segments: [] }))
}))

vi.mock('@timur00kh/whisper.wasm', () => ({
  convertFromFile: vi.fn(async () => ({ audioData: new Float32Array(16_000) })),
  ModelManager: class {
    async loadModelByUrl() { return new Uint8Array(1) }
  },
  WhisperWasmService: class {
    initModel = initModel
    transcribe = transcribeModel
  }
}))

it('checks the backend even when the browser reports online', async () => {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  const timeout = vi.spyOn(AbortSignal, 'timeout')
  try {
    fetch.mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok' })))
    expect(await checkBackendAvailable()).toBe(true)
    expect(fetch).toHaveBeenCalledWith('/api/health', {
      cache: 'no-store', signal: expect.any(AbortSignal)
    })
    expect(timeout).toHaveBeenCalledWith(1500)
    fetch.mockResolvedValueOnce(new Response('', { status: 503 }))
    expect(await checkBackendAvailable()).toBe(false)
    fetch.mockRejectedValueOnce(new TypeError('Load failed'))
    expect(await checkBackendAvailable()).toBe(false)
    fetch.mockRejectedValueOnce(new DOMException('Timed out', 'TimeoutError'))
    expect(await checkBackendAvailable()).toBe(false)
    fetch.mockResolvedValueOnce(new Response('<html>Cached page</html>'))
    expect(await checkBackendAvailable()).toBe(false)
  } finally {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  }
})

it('rejects transcription when its worker fails', async () => {
  const postMessage = vi.fn()
  const terminate = vi.fn()
  const audioContext = vi.fn()
  let activeWorker: Worker
  let offline: ReturnType<typeof useOfflineTranscription>
  vi.stubGlobal('AudioContext', audioContext)
  vi.stubGlobal('Worker', class {
    postMessage = postMessage
    terminate = terminate
    constructor() {
      activeWorker = this as unknown as Worker
    }
  })
  const component = await mountSuspended(defineComponent({
    setup() {
      useRuntimeConfig().public.offlineWhisperModelVersion = 'test'
      offline = useOfflineTranscription()
      onMounted(() => offline.prepare())
      return () => h('div')
    }
  }))
  try {
    expect(offline!.state.value).toBe('loading')
    const response = offline!.transcribe(new Blob(['audio']))
    const rejection = expect(response).rejects.toThrow('WASM thread failed')
    await Promise.resolve()
    expect(postMessage).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: 'transcribe' }), expect.any(Array)
    )
    activeWorker!.onmessage!(new MessageEvent('message', { data: { type: 'ready' } }))
    await vi.waitFor(() => expect(postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'transcribe' }), expect.any(Array)
    ))
    activeWorker!.onerror!(new ErrorEvent('error', { message: 'WASM thread failed' }))
    await rejection
    expect(offline!.state.value).toBe('failed')
    expect(terminate).toHaveBeenCalledOnce()
    await expect(offline!.transcribe(new Blob(['audio']))).rejects.toThrow('WASM thread failed')
  } finally {
    component.unmount()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  }
})

it('starts the WASM thread before it marks the model ready', async () => {
  const messages = vi.fn()
  const workerScope = { onmessage: undefined as undefined | ((event: MessageEvent) => void) }
  let finishWarmup: (value: { segments: [] }) => void
  transcribeModel.mockImplementationOnce(() => new Promise((resolve) => {
    finishWarmup = resolve
  }))
  vi.stubGlobal('self', workerScope)
  vi.spyOn(navigator, 'hardwareConcurrency', 'get').mockReturnValue(8)
  vi.stubGlobal('postMessage', messages)
  try {
    await import('~/workers/offlineWhisper.worker')
    workerScope.onmessage!(new MessageEvent('message', {
      data: { type: 'prepare', modelUrl: '/model.bin' }
    }))
    await vi.waitFor(() => expect(transcribeModel).toHaveBeenCalledWith(
      expect.any(Float32Array), undefined, { language: 'de', threads: 4, translate: false }
    ))
    expect(initModel).toHaveBeenCalledOnce()
    expect(messages).not.toHaveBeenCalledWith({ type: 'ready' })
    finishWarmup!({ segments: [] })
    await vi.waitFor(() => expect(messages).toHaveBeenCalledWith({ type: 'ready' }))
  } finally {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  }
})
