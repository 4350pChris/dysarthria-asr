import { expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, ref } from 'vue'
import { useSpeechSession } from '~/composables/useSpeechSession'
import type { TranscriptionResult } from '~/types/speech'

mockNuxtImport('useSpeechCommands', () => () => ({ speak: vi.fn() }))
mockNuxtImport('useUsageAnalytics', () => () => ({ track: vi.fn() }))

it('saves the latest correction after an in-flight save and permits retry after failure', async () => {
  let speech!: ReturnType<typeof useSpeechSession>
  const view = await mountSuspended(defineComponent({ setup() {
    speech = useSpeechSession(ref('text'), ref(true))
    return () => h('div')
  } }))
  vi.useFakeTimers()
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  let complete!: (value: { ok: boolean }) => void
  fetch.mockReturnValueOnce(new Promise((resolve) => {
    complete = resolve
  }))
  speech.result.value = { audio_id: 'original' } as TranscriptionResult
  speech.setFreeText('First correction')
  await vi.advanceTimersByTimeAsync(500)
  speech.setFreeText('Latest correction')
  await vi.advanceTimersByTimeAsync(500)
  expect(fetch).toHaveBeenCalledOnce()
  fetch.mockResolvedValueOnce({ ok: false })
  complete({ ok: true })
  await vi.advanceTimersByTimeAsync(500)
  expect(JSON.parse(fetch.mock.calls[1]![1].body)).toMatchObject({ transcript: 'Latest correction', status: 'draft' })
  expect(speech.status.value).toContain('noch nicht gespeichert')
  fetch.mockResolvedValueOnce({ ok: true })
  speech.setFreeText('Latest correction')
  await vi.advanceTimersByTimeAsync(500)
  expect(fetch).toHaveBeenCalledTimes(3)
  view.unmount()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})
