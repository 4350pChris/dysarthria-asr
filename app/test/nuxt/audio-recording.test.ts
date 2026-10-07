import { expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h } from 'vue'
import { useAudioRecording } from '~/composables/useAudioRecording'

const mocks = vi.hoisted(() => ({ silenceStop: undefined as (() => void) | undefined }))
mockNuxtImport('useSilenceDetection', () => (onStop: () => void) => {
  mocks.silenceStop = onStop
  return { start: vi.fn(), stop: vi.fn() }
})

it('reports actual recording starts and preserves silence and voice stop reasons', async () => {
  const onStarted = vi.fn()
  const onStopping = vi.fn()
  const trackStop = vi.fn()
  const mediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: trackStop }] }) }
  })
  class Recorder {
    state = 'inactive'
    mimeType = 'audio/webm'
    onstop?: () => Promise<void>
    start() { this.state = 'recording' }
    stop() {
      this.state = 'inactive'
      void this.onstop?.()
    }
  }
  vi.stubGlobal('MediaRecorder', Recorder)
  let audio!: ReturnType<typeof useAudioRecording>
  const view = await mountSuspended(defineComponent({ setup() {
    audio = useAudioRecording({ onComplete: vi.fn(), onStarted, onStopping })
    return () => h('div')
  } }))
  try {
    const first = audio.start()
    expect(onStarted).not.toHaveBeenCalled()
    await Promise.resolve()
    expect(audio.isRecording.value).toBe(true)
    expect(onStarted).toHaveBeenCalledOnce()
    mocks.silenceStop!()
    await first
    expect(onStopping).toHaveBeenLastCalledWith('silence')
    const second = audio.start()
    await Promise.resolve()
    audio.stop('voice_command')
    audio.stop()
    await second
    expect(onStopping).toHaveBeenCalledTimes(2)
    expect(onStopping).toHaveBeenLastCalledWith('voice_command')
    expect(trackStop).toHaveBeenCalledTimes(2)
  } finally {
    view.unmount()
    if (mediaDevices) Object.defineProperty(navigator, 'mediaDevices', mediaDevices)
    else Reflect.deleteProperty(navigator, 'mediaDevices')
    vi.unstubAllGlobals()
  }
})
