import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import type { Ref } from 'vue'
import TranscriptReview from '~/components/TranscriptReview.vue'

type Command = { id: string, enabled: () => boolean, handler: () => void | Promise<void> }
const mocks = vi.hoisted(() => ({
  fetch: vi.fn(),
  commands: [] as Command[],
  pause: vi.fn(),
  resume: vi.fn(),
  start: vi.fn(),
  autoStopOnSilence: undefined as undefined | Ref<boolean>,
  complete: undefined as undefined | ((blob: Blob) => Promise<void>)
}))
mockNuxtImport('useSpeechCommands', () => () => ({
  pause: mocks.pause,
  speak: vi.fn(),
  register: (command: Command) => {
    mocks.commands.push(command)
    return () => {
      mocks.commands = mocks.commands.filter(item => item !== command)
    }
  }
}))
mockNuxtImport('useSpeechCommand', () => (command: Command) => {
  mocks.commands.push(command)
})
mockNuxtImport('useAudioRecording', () => (options: { onComplete: (blob: Blob) => Promise<void>, autoStopOnSilence: Ref<boolean> }) => {
  expect(options).not.toHaveProperty('silenceMs')
  mocks.autoStopOnSilence = options.autoStopOnSilence
  mocks.complete = options.onComplete
  return { isRecording: ref(false), audioLevel: ref(0), start: mocks.start, stop: vi.fn() }
})

beforeEach(() => {
  mocks.commands = []
  mocks.fetch.mockReset()
  mocks.start.mockReset()
  mocks.pause.mockReset().mockReturnValue(mocks.resume)
  mocks.resume.mockReset()
  vi.stubGlobal('$fetch', mocks.fetch)
})
afterEach(() => vi.unstubAllGlobals())
const command = (id: string) => mocks.commands.find(command => command.id === id)!

it('marks the exact phrase, applies only on approval, shifts later marks, and undoes', async () => {
  const original = '🤍 Ich hatte mein Brot bewohnen. Danach trank ich Kaffe.'
  mocks.fetch.mockResolvedValue({ suggestions: [
    { original: 'Brot bewohnen', replacement: 'Probewohnen' },
    { original: 'Kaffe', replacement: 'Kaffee' }
  ] })
  const view = await mountSuspended(TranscriptReview, { props: { text: original, audioId: 'one' } })
  await flushPromises()
  expect(view.findAll('mark').map(mark => mark.text())).toEqual(['Brot bewohnen1', 'Kaffe2'])
  expect(view.emitted('updateText')).toBeUndefined()
  expect(command('accept-correction').enabled()).toBe(false)
  await view.findAll('button').find(button => button.text() === 'Prüfen')!.trigger('click')
  expect(command('accept-correction').enabled()).toBe(true)
  await view.findAll('button').find(button => button.text() === 'Übernehmen')!.trigger('click')
  const corrected = '🤍 Ich hatte mein Probewohnen. Danach trank ich Kaffe.'
  expect(view.emitted('updateText')!.at(-1)).toEqual([corrected])
  await view.setProps({ text: corrected })
  expect(view.findAll('mark').map(mark => mark.text())).toEqual(['Kaffe2'])
  await view.findAll('button').find(button => button.text() === 'Behalten')!.trigger('click')
  command('undo-correction').handler()
  expect(view.emitted('updateText')!.at(-1)).toEqual([original])
  await view.find('audio').trigger('play')
  expect(mocks.pause).toHaveBeenCalledOnce()
  await view.find('audio').trigger('error')
  await view.find('audio').trigger('play')
  expect(mocks.pause).toHaveBeenCalledTimes(2)
  view.unmount()
})

it('discards a checker reply after editing or starting another recording', async () => {
  let reply!: (value: unknown) => void
  mocks.fetch.mockReturnValue(new Promise((resolve) => {
    reply = resolve
  }))
  const view = await mountSuspended(TranscriptReview, { props: { text: 'Brot bewohnen', audioId: 'one' } })
  const signal = mocks.fetch.mock.calls[0]![1].signal as AbortSignal
  await view.setProps({ text: 'Probewohnen' })
  expect(signal.aborted).toBe(true)
  reply({ suggestions: [{ original: 'Brot bewohnen', replacement: 'Probewohnen' }] })
  await flushPromises()
  expect(view.findAll('mark')).toHaveLength(0)
  expect(view.emitted('updateText')).toBeUndefined()
  await view.setProps({ audioId: 'two', text: 'Neuer Text' })
  expect(mocks.fetch).toHaveBeenCalledTimes(2)
  view.unmount()
})

it('allows voice sentence selection when the checker fails and confirms replacement speech', async () => {
  mocks.fetch.mockRejectedValueOnce(new Error('offline'))
  const original = 'Hallo. Ich hatte mein Brot bewohnen.'
  const view = await mountSuspended(TranscriptReview, { props: { text: original, audioId: 'one' } })
  await flushPromises()
  expect(view.text()).toContain('Textprüfung nicht verfügbar')
  command('correct-sentence').handler()
  expect(command('correct-sentence-2').enabled()).toBe(true)
  command('correct-sentence-2').handler()
  let finishRecognition!: (result: { text: string }) => void
  mocks.fetch.mockReturnValueOnce(new Promise((resolve) => {
    finishRecognition = resolve
  }))
  mocks.start.mockImplementationOnce(async () => {
    await mocks.complete!(new Blob(['audio']))
  })
  const pending = command('record-correction').handler()
  await flushPromises()
  expect(view.emitted('busy')!.at(-1)).toEqual([true])
  expect(command('accept-correction').enabled()).toBe(false)
  expect(view.findAll('[role="status"]').filter(status => status.text() === 'Dein Ausdruck wird erkannt …')).toHaveLength(1)
  await command('record-correction').handler()
  expect(mocks.start).toHaveBeenCalledOnce()
  finishRecognition({ text: 'Ich hatte mein Probewohnen.' })
  await pending
  await flushPromises()
  expect(view.emitted('busy')!.at(-1)).toEqual([false])
  expect(mocks.pause).toHaveBeenCalledOnce()
  expect(mocks.resume).toHaveBeenCalledOnce()
  expect(view.emitted('updateText')).toBeUndefined()
  expect(view.text()).toContain('Meintest du: Ich hatte mein Probewohnen.')
  command('accept-correction').handler()
  expect(view.emitted('updateText')!.at(-1)).toEqual(['Hallo. Ich hatte mein Probewohnen.'])
  view.unmount()
})

it('starts the check after the final recording becomes ready', async () => {
  mocks.fetch.mockResolvedValue({ suggestions: [] })
  const view = await mountSuspended(TranscriptReview, { props: { text: 'Hallo', disabled: true } })
  await view.setProps({ audioId: 'one' })
  expect(mocks.fetch).not.toHaveBeenCalled()
  await view.setProps({ disabled: false })
  await flushPromises()
  expect(mocks.fetch).toHaveBeenCalledOnce()
  view.unmount()
})

it('uses the saved silence stop setting for correction recordings', async () => {
  localStorage.setItem('auto-stop-on-silence', 'false')
  const view = await mountSuspended(TranscriptReview, { props: { text: 'Hallo' } })
  expect(mocks.autoStopOnSilence!.value).toBe(false)
  view.unmount()
  localStorage.removeItem('auto-stop-on-silence')
})
