import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { flushPromises } from '@vue/test-utils'
import TranscriptReview from '~/components/TranscriptReview.vue'

type Command = { id: string, enabled: () => boolean, handler: () => void | Promise<void> }
const mocks = vi.hoisted(() => ({
  fetch: vi.fn(),
  commands: [] as Command[],
  speak: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn()
}))
mockNuxtImport('useSpeechCommands', () => () => ({
  pause: mocks.pause,
  speak: mocks.speak
}))
mockNuxtImport('useSpeechCommand', () => (command: Command) => {
  mocks.commands.push(command)
})
beforeEach(() => {
  mocks.speak.mockReset()
  mocks.commands = []
  mocks.fetch.mockReset()
  mocks.pause.mockReset().mockReturnValue(mocks.resume)
  mocks.resume.mockReset()
  vi.stubGlobal('$fetch', mocks.fetch)
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})
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
  expect(document.querySelector('[role=dialog]')).toBeNull()
  await view.findAll('button').find(button => button.text() === 'Prüfen')!.trigger('click')
  await flushPromises()
  const dialog = () => document.querySelector('[role=dialog]')!
  const button = (label: string) => [...dialog().querySelectorAll('button')].find(button => button.textContent?.trim() === label)!
  expect(dialog().textContent).toContain('Stelle 1 von 2')
  expect(dialog().textContent).not.toContain('Danach trank ich')
  dialog().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  await flushPromises()
  expect(dialog()).not.toBeNull()
  expect(dialog().textContent).not.toContain('Neu sprechen')
  expect(dialog().textContent).not.toContain('Vorlesen')
  expect(mocks.speak.mock.calls.every(call => call[0] === '')).toBe(true)
  expect(mocks.commands.map(command => command.id)).toEqual([
    'review', 'accept-correction', 'keep-correction', 'undo-correction', 'play-recording', 'close-review'
  ])
  expect(command('accept-correction').enabled()).toBe(true)
  vi.useFakeTimers()
  button('Übernehmen').click()
  command('accept-correction').handler()
  expect(view.emitted('updateText')).toHaveLength(1)
  const corrected = '🤍 Ich hatte mein Probewohnen. Danach trank ich Kaffe.'
  expect(view.emitted('updateText')!.at(-1)).toEqual([corrected])
  await view.setProps({ text: corrected })
  expect(view.findAll('mark').map(mark => mark.text())).toEqual(['Kaffe2'])
  expect(dialog().textContent).toContain('Stelle 2 von 2')
  expect(command('keep-correction').enabled()).toBe(false)
  button('Rückgängig').click()
  expect(view.emitted('updateText')!.at(-1)).toEqual([original])
  await view.setProps({ text: original })
  expect(dialog().textContent).toContain('Stelle 1 von 2')
  button('Übernehmen').click()
  await view.setProps({ text: corrected })
  await vi.advanceTimersByTimeAsync(2_000)
  button('Behalten').click()
  await flushPromises()
  expect(dialog().textContent).toContain('Prüfung beendet')
  expect(view.emitted('active')!.at(-1)).toEqual([true])
  button('Rückgängig').click()
  await flushPromises()
  expect(dialog().textContent).toContain('Stelle 2 von 2')
  expect(view.emitted('updateText')!.at(-1)).toEqual([corrected])
  button('Schließen').click()
  await flushPromises()
  expect(document.querySelector('[role=dialog]')).toBeNull()
  expect(view.emitted('active')!.at(-1)).toEqual([false])
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

it('keeps direct text editing available when the checker fails', async () => {
  mocks.fetch.mockRejectedValueOnce(new Error('offline'))
  const view = await mountSuspended(TranscriptReview, { props: { text: 'Hallo.', audioId: 'one' } })
  await flushPromises()
  expect(view.text()).toContain('Textprüfung nicht verfügbar. Du kannst den Text direkt bearbeiten.')
  expect(view.find('textarea').attributes('readonly')).toBeUndefined()
  await view.find('textarea').setValue('Guten Tag.')
  expect(view.emitted('updateText')!.at(-1)).toEqual(['Guten Tag.'])
  expect(mocks.fetch).toHaveBeenCalledOnce()
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
