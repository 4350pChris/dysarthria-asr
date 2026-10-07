import { afterEach, expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, ref } from 'vue'
import { useSpeechSession } from '~/composables/useSpeechSession'

const mocks = vi.hoisted(() => ({
  recording: undefined as unknown as {
    onComplete: (blob: Blob) => Promise<void>
    onStarted: () => void
    onStopping: (reason: string) => void
  },
  live: undefined as unknown as { onText: (text: string) => void },
  start: vi.fn(),
  track: vi.fn(),
  control: vi.fn()
}))
mockNuxtImport('useSpeechCommands', () => () => ({ speak: vi.fn() }))
mockNuxtImport('useUsageAnalytics', () => () => ({ track: mocks.track, control: mocks.control }))
mockNuxtImport('useBackendAvailability', () => () => ref(true))
mockNuxtImport('useOfflineTranscription', () => () => ({ prepare: vi.fn() }))
mockNuxtImport('useLiveTranscription', () => (options: typeof mocks.live) => {
  mocks.live = options
  return { start: vi.fn(), stop: vi.fn() }
})
mockNuxtImport('useAudioRecording', () => (options: typeof mocks.recording) => {
  mocks.recording = options
  return { start: mocks.start, stop: vi.fn(), isRecording: ref(false), audioLevel: ref(0) }
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

it('uploads only fresh segments, preserves edits and failures, and never labels combined text', async () => {
  let speech!: ReturnType<typeof useSpeechSession>
  const view = await mountSuspended(defineComponent({ setup() {
    speech = useSpeechSession(ref('text'), ref(false))
    return () => h('div')
  } }))
  vi.useFakeTimers()
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ audio_id: 'first', emoji_text: 'Hallo' }) })
  vi.stubGlobal('fetch', fetch)
  try {
    await speech.startRecording()
    await speech.startRecording()
    expect(mocks.start).toHaveBeenCalledOnce()
    expect(mocks.track).not.toHaveBeenCalledWith('recording_started', expect.anything())
    mocks.recording.onStarted()
    expect(mocks.track).toHaveBeenCalledWith('recording_started', expect.objectContaining({ trigger: 'unknown', auto_stop_enabled: false }))
    mocks.recording.onStopping('silence')
    expect(mocks.track).toHaveBeenCalledWith('recording_stopped', expect.objectContaining({ reason: 'silence' }))
    const first = new Blob(['first audio'])
    await mocks.recording.onComplete(first)
    speech.setFreeText('Hallo!')
    await vi.advanceTimersByTimeAsync(2_000)
    fetch.mockClear()
    await speech.startRecording()
    mocks.recording.onStarted()
    expect(mocks.track).toHaveBeenCalledWith('recording_resumed', expect.objectContaining({ previous_stop_reason: 'silence', ready_to_restart_ms: 2000 }))
    mocks.live.onText('Welt')
    expect(speech.freeText.value).toBe('Hallo! Welt')
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ audio_id: 'second', emoji_text: 'Welt.' }) })
    const second = new Blob(['second audio'])
    await mocks.recording.onComplete(second)
    expect(fetch).toHaveBeenCalledOnce()
    const uploaded = fetch.mock.calls[0]![1].body.get('audio') as Blob
    expect(uploaded.size).toBe(second.size)
    expect(uploaded.size).not.toBe(first.size + second.size)
    expect(speech.freeText.value).toBe('Hallo! Welt.')
    expect(mocks.track).toHaveBeenCalledWith('transcription_completed', expect.objectContaining({ engine: 'online', outcome: 'text_recognized', stop_to_result_ms: expect.any(Number) }))
    expect(speech.audioId.value).toBeUndefined()
    speech.setFreeText('Hallo, Welt!')
    await vi.advanceTimersByTimeAsync(2_000)
    expect(fetch).toHaveBeenCalledOnce()

    mocks.start.mockRejectedValueOnce(new Error('No microphone'))
    await speech.startRecording()
    expect(speech.freeText.value).toBe('Hallo, Welt!')
    expect(mocks.track).toHaveBeenCalledWith('recording_start_failed', expect.objectContaining({ error_code: 'unknown' }))
    await vi.advanceTimersByTimeAsync(2_000)
    await speech.startRecording()
    mocks.live.onText('Unfinished')
    fetch.mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Fehler.' }) })
    await mocks.recording.onComplete(new Blob(['failed audio']))
    expect(speech.freeText.value).toBe('Hallo, Welt!')
    expect(speech.status.value).toBe('Fehler.')
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ audio_id: 'empty', emoji_text: '' }) })
    await mocks.recording.onComplete(new Blob(['empty result']))
    expect(mocks.track).toHaveBeenCalledWith('transcription_completed', expect.objectContaining({ outcome: 'no_result' }))
    speech.resetText()
    mocks.track.mockClear()
    await vi.advanceTimersByTimeAsync(2_000)
    await speech.startRecording()
    mocks.recording.onStarted()
    expect(mocks.track).not.toHaveBeenCalledWith('recording_resumed', expect.anything())
    expect(speech.freeText.value).toBe('')
    expect(speech.result.value).toBeUndefined()
  } finally {
    view.unmount()
  }
})
