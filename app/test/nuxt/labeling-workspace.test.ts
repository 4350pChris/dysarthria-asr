import { beforeEach, expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { ref } from 'vue'
import LabelingWorkspace from '~/components/LabelingWorkspace.vue'

const { fetchItems } = vi.hoisted(() => ({ fetchItems: vi.fn() }))
mockNuxtImport('useFetch', () => fetchItems)

beforeEach(() => {
  fetchItems.mockReset()
})

it('opens clips, sends page and filter queries, and protects unsaved notes', async () => {
  const items = ['first', 'second'].map(audio_id => ({
    audio_id,
    audio_file: `${audio_id}.ogg`,
    original_filename: `${audio_id}.ogg`,
    source: 'whatsapp_upload',
    created_at: '2026-09-30T12:00:00Z',
    asr_text: audio_id,
    transcript: '',
    notes: '',
    status: 'draft',
    unsure: false
  }))
  fetchItems.mockResolvedValue({
    data: ref({ items, filtered_count: 51, counts: { draft: 51, labeled: 0, skipped: 0, total: 51 } }),
    status: ref('success'),
    error: ref(null),
    refresh: vi.fn()
  })
  const component = await mountSuspended(LabelingWorkspace)
  const query = fetchItems.mock.calls[0]![1].query
  expect(query.value).toMatchObject({ order: 'newest', offset: 0, limit: 25 })
  const button = (text: string) => component.findAll('button').find(button => button.text() === text)!
  await component.findAll('tbody button')[1]!.trigger('click')
  expect(component.find('audio').attributes('src')).toBe('/api/labeling/audio/second')
  await button('Nächste Seite').trigger('click')
  expect(query.value.offset).toBe(25)
  await component.find('input[placeholder="Aufnahmen suchen …"]').setValue('coffee')
  expect(query.value).toMatchObject({ search: 'coffee', offset: 0 })
  await component.find('input[placeholder="Alle Notizen"]').setValue('noisy')
  expect(query.value.notes).toBe('noisy')
  await component.findAll('textarea').at(-1)!.setValue('noisy')
  expect(button('Nächste Seite').attributes('disabled')).toBeDefined()
  expect(component.findAll('tbody button')[0]!.attributes('disabled')).toBeDefined()
  await button('Änderungen verwerfen').trigger('click')
  expect(button('Nächste Seite').attributes('disabled')).toBeUndefined()
  component.unmount()
})
