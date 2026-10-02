import { afterEach, expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import SpeechWorkspace from '~/components/SpeechWorkspace.vue'

function makeSession() {
  return {
    freeText: ref(''), result: ref<{ audio_id: string }>(), isBusy: ref(false), isRecording: ref(false),
    status: ref(''), emojiHistory: ref([]), hasEmojiResult: ref(false), audioLevel: ref(0),
    startRecording: vi.fn(), stopRecording: vi.fn(), speakSelected: vi.fn(), copySelected: vi.fn(),
    shareText: vi.fn(), shareToInstagram: vi.fn(), setFreeText: vi.fn()
  }
}

const mocks = vi.hoisted(() => ({ session: undefined as ReturnType<typeof makeSession> | undefined }))
mockNuxtImport('useSpeechSession', () => () => mocks.session)
mockNuxtImport('useSpeechCommand', () => () => {})
mockNuxtImport('useSpeechCommands', () => () => ({
  isListening: ref(false), isSupported: ref(true), status: ref(''),
  speak: vi.fn(), pause: () => () => {}, start: vi.fn(), stop: vi.fn()
}))
afterEach(() => vi.restoreAllMocks())

it('puts recording first and scrolls once to the final text before review finishes', async () => {
  const scroll = vi.fn()
  const oldScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView')
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: scroll })
  mocks.session = makeSession()
  const view = await mountSuspended(SpeechWorkspace, {
    props: { mode: 'text' },
    global: { stubs: { FreeTextResult: true, SpeechCommandControl: true, SilenceStopSetting: true, AudioLevelMeter: true } }
  })
  try {
    expect(view.findAll('button')[0]!.text()).toContain('Aufnehmen')
    mocks.session.isRecording.value = true
    mocks.session.freeText.value = 'Live text'
    await flushPromises()
    expect(scroll).not.toHaveBeenCalled()
    mocks.session.isRecording.value = false
    mocks.session.isBusy.value = true
    await flushPromises()
    mocks.session.result.value = { audio_id: 'one' }
    mocks.session.freeText.value = 'Final text'
    await flushPromises()
    expect(scroll).not.toHaveBeenCalled()
    mocks.session.isBusy.value = false
    await flushPromises()
    expect(scroll).toHaveBeenCalledExactlyOnceWith({ block: 'start', behavior: 'instant' })
    expect(view.find('button').text()).toContain('Neue Aufnahme')
    expect(view.find('button').classes()).toContain('min-h-60')
    expect(view.find('.fixed').exists()).toBe(false)
    mocks.session.freeText.value = 'Edited text'
    await flushPromises()
    expect(scroll).toHaveBeenCalledOnce()
  } finally {
    view.unmount()
    if (oldScroll) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', oldScroll)
    else Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
  }
})
