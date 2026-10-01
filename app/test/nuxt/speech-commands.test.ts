import { expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h } from 'vue'
import { createSpeechCommands } from '~/composables/useSpeechCommands'

const mocks = vi.hoisted(() => ({ recognition: {
  start: vi.fn(), stop: vi.fn(),
  onend: undefined as undefined | (() => void),
  onresult: undefined as undefined | ((event: unknown) => void)
} }))
vi.mock('~/utils/speechRecognition', () => ({
  createSpeechRecognition: () => mocks.recognition,
  supportsSpeechRecognition: () => true
}))
mockNuxtImport('useUsageAnalytics', () => () => ({ track: vi.fn() }))

it('limits active commands, pauses for speech, and respects stop while paused', async () => {
  vi.stubGlobal('SpeechSynthesisUtterance', class {
    lang = ''
    onend: (() => void) | null = null
    onerror: (() => void) | null = null
    constructor(public text: string) {}
  })
  let spoken!: SpeechSynthesisUtterance
  vi.stubGlobal('speechSynthesis', { speaking: false, cancel: vi.fn(), speak: (utterance: SpeechSynthesisUtterance) => {
    spoken = utterance
  } })
  let commands!: ReturnType<typeof createSpeechCommands>
  const view = await mountSuspended(defineComponent({
    setup() {
      commands = createSpeechCommands()
      return () => h('div')
    }
  }))
  mocks.recognition.stop.mockImplementation(() => mocks.recognition.onend?.())
  const disabled = vi.fn()
  const accept = vi.fn()
  commands.register({ id: 'hidden', label: 'Übernehmen', phrases: ['übernehmen'], enabled: () => false, handler: disabled })
  commands.register({ id: 'accept', label: 'Übernehmen', phrases: ['übernehmen'], handler: accept })
  const result = () => mocks.recognition.onresult?.({ results: [[{ transcript: 'übernehmen' }]] })
  commands.start()
  result()
  expect(accept).toHaveBeenCalledOnce()
  expect(disabled).not.toHaveBeenCalled()
  const resume = commands.pause()
  const resumeAgain = commands.pause()
  result()
  resume()
  expect(mocks.recognition.start).toHaveBeenCalledOnce()
  resumeAgain()
  expect(mocks.recognition.start).toHaveBeenCalledTimes(2)
  commands.speak('Übernehmen')
  result()
  expect(accept).toHaveBeenCalledOnce()
  spoken.onend?.(new Event('end') as SpeechSynthesisEvent)
  result()
  expect(accept).toHaveBeenCalledTimes(2)
  const lastResume = commands.pause()
  commands.stop()
  lastResume()
  expect(commands.isListening.value).toBe(false)
  expect(mocks.recognition.start).toHaveBeenCalledTimes(3)
  view.unmount()
  vi.unstubAllGlobals()
})
