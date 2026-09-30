<script setup lang="ts">
import type { AudioSource, LabelItem, LabelStatus } from '~/types/speech'

type ItemsResponse = {
  items: LabelItem[]
  filtered_count: number
  counts: Record<LabelStatus | 'total', number>
}

const sourceOptions = [
  { label: 'Alle Quellen', value: 'all' },
  { label: 'App-Aufnahmen', value: 'app_recording' },
  { label: 'Geführtes Lesen', value: 'training_reading' },
  { label: 'WhatsApp', value: 'whatsapp_upload' }
]
const statusOptions = [
  { label: 'Entwürfe', value: 'draft' },
  { label: 'Gelabelt', value: 'labeled' },
  { label: 'Übersprungen', value: 'skipped' },
  { label: 'Alle', value: 'all' }
]

const currentIndex = ref(0)
const sourceFilter = ref<AudioSource | 'all'>('all')
const statusFilter = ref<LabelStatus | 'all'>('all')
const search = ref('')
const notesFilter = ref('')
const order = ref('newest')
const page = ref(1)
const pageSize = 25
const saveError = ref('')
const unsureOnly = ref(false)
const missingAsrOnly = ref(false)
const transcript = ref('')
const notes = ref('')
const unsure = ref(false)
const isSaving = ref(false)

const emptyCounts: Record<LabelStatus | 'total', number> = {
  draft: 0,
  labeled: 0,
  skipped: 0,
  total: 0
}

const itemsQuery = computed(() => ({
  search: search.value.trim(),
  notes: notesFilter.value.trim(),
  order: order.value,
  limit: pageSize,
  offset: (page.value - 1) * pageSize,
  ...(sourceFilter.value !== 'all' ? { source: sourceFilter.value } : {}),
  ...(statusFilter.value !== 'all' ? { status: statusFilter.value } : {}),
  ...(unsureOnly.value ? { unsure: true } : {}),
  ...(missingAsrOnly.value ? { missing_asr: true } : {})
}))

const {
  data: itemsData,
  refresh: refreshItems,
  status: fetchStatus,
  error: fetchError
} = await useFetch<ItemsResponse>('/api/labeling/items', {
  query: itemsQuery,
  default: () => ({ items: [], filtered_count: 0, counts: emptyCounts })
})

const items = computed(() => itemsData.value.items)
const filteredCount = computed(() => itemsData.value.filtered_count)
const counts = computed(() => itemsData.value.counts)
const pageCount = computed(() => Math.max(1, Math.ceil(filteredCount.value / pageSize)))
const busy = computed(() => isSaving.value || fetchStatus.value === 'pending')
const dirty = computed(() => Boolean(current.value) && (
  transcript.value !== (current.value?.transcript || current.value?.asr_text || '')
  || notes.value !== (current.value?.notes || '')
  || unsure.value !== Boolean(current.value?.unsure)
))
const editor = ref<HTMLElement>()
const current = computed(() => items.value[currentIndex.value])
const audioUrl = computed(() =>
  current.value ? `/api/labeling/audio/${current.value.audio_id}` : ''
)
const recordedAt = computed(() => current.value ? formatDate(current.value.created_at) : '')
const navigationLabel = computed(() =>
  statusFilter.value === 'draft'
    ? `Noch ${items.value.length} zu prüfen`
    : `${currentIndex.value + 1} von ${items.value.length} auf dieser Seite`
)

watch(
  current,
  (item) => {
    transcript.value = item?.transcript || item?.asr_text || ''
    notes.value = item?.notes || ''
    saveError.value = ''
    unsure.value = Boolean(item?.unsure)
  },
  { immediate: true }
)

watch([sourceFilter, statusFilter, unsureOnly, missingAsrOnly, search, notesFilter, order], () => {
  page.value = 1
  currentIndex.value = 0
})

watch(page, () => {
  currentIndex.value = 0
})

watch(pageCount, (count) => {
  if (page.value > count) page.value = count
})

watch(items, (nextItems) => {
  if (currentIndex.value >= nextItems.length) currentIndex.value = 0
})

async function save(nextStatus: LabelStatus) {
  if (!current.value || isSaving.value) return
  const savedId = current.value.audio_id
  isSaving.value = true
  saveError.value = ''
  try {
    await $fetch(`/api/labeling/items/${current.value.audio_id}`, {
      method: 'PATCH',
      body: {
        notes: notes.value.trim(),
        status: nextStatus,
        transcript: transcript.value.trim(),
        unsure: unsure.value
      }
    })
    await refreshItems()
    const savedItemIndex = items.value.findIndex(item => item.audio_id === savedId)
    if (savedItemIndex === -1) {
      if (currentIndex.value >= items.value.length) currentIndex.value = 0
    } else if (items.value.length > 1) {
      currentIndex.value = (savedItemIndex + 1) % items.value.length
    }
  } catch {
    saveError.value = 'Speichern fehlgeschlagen. Bitte erneut versuchen.'
  } finally {
    isSaving.value = false
  }
}

function discardChanges() {
  transcript.value = current.value?.transcript || current.value?.asr_text || ''
  notes.value = current.value?.notes || ''
  unsure.value = Boolean(current.value?.unsure)
}

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function selectItem(index: number) {
  if (dirty.value || busy.value) return
  currentIndex.value = index
  nextTick(() => editor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

function moveCurrent(delta: number) {
  if (!items.value.length || dirty.value || busy.value) return
  currentIndex.value
    = (currentIndex.value + delta + items.value.length) % items.value.length
}
</script>

<template>
  <div class="space-y-5">
    <fieldset
      :disabled="dirty || isSaving"
      class="grid gap-3 sm:grid-cols-3"
    >
      <UFormField
        label="Suche"
        help="Dateiname, Audio-ID, Text oder Notizen"
      >
        <UInput
          v-model="search"
          :disabled="dirty || isSaving"
          class="w-full"
          icon="i-lucide-search"
          placeholder="Aufnahmen suchen …"
          :maxlength="200"
        />
      </UFormField>
      <UFormField
        label="Notizen enthalten"
        help="Zum Beispiel noisy"
      >
        <UInput
          v-model="notesFilter"
          :disabled="dirty || isSaving"
          class="w-full"
          placeholder="Alle Notizen"
          :maxlength="200"
        />
      </UFormField>
      <UFormField label="Reihenfolge">
        <USelect
          v-model="order"
          :disabled="dirty || isSaving"
          class="w-full"
          :items="[{ label: 'Neueste zuerst', value: 'newest' }, { label: 'Älteste zuerst', value: 'oldest' }]"
        />
      </UFormField>
      <UFormField label="Quelle">
        <USelect
          v-model="sourceFilter"
          :disabled="dirty || isSaving"
          class="w-full"
          :items="sourceOptions"
          size="lg"
        />
      </UFormField>
      <UFormField label="Status">
        <USelect
          v-model="statusFilter"
          :disabled="dirty || isSaving"
          class="w-full"
          :items="statusOptions"
          size="lg"
        />
      </UFormField>
      <div class="space-y-3 self-center">
        <UCheckbox
          v-model="unsureOnly"
          :disabled="dirty || isSaving"
          label="Nur unsichere"
          size="lg"
        />
        <UCheckbox
          v-model="missingAsrOnly"
          :disabled="dirty || isSaving"
          label="Ohne ASR-Text"
          size="lg"
        />
      </div>
    </fieldset>

    <p class="text-sm font-semibold text-muted">
      {{ counts.draft }} offen · {{ counts.labeled }} gelabelt ·
      {{ counts.skipped }} übersprungen
    </p>

    <EmptyAsrBulkDeletion
      v-if="missingAsrOnly && !dirty && !busy && !fetchError"
      :search="search.trim()"
      :notes="notesFilter.trim()"
      :count="filteredCount"
      :source="sourceFilter"
      :status="statusFilter"
      :unsure-only="unsureOnly"
      @deleted="refreshItems"
    />

    <p
      v-if="dirty"
      class="text-sm text-muted"
      role="status"
    >
      Bitte Änderungen speichern oder verwerfen, bevor du eine andere Aufnahme wählst.
      <UButton
        color="neutral"
        variant="link"
        :disabled="busy"
        @click="discardChanges"
      >
        Änderungen verwerfen
      </UButton>
    </p>

    <div
      v-if="fetchError"
      role="alert"
      class="rounded-lg border border-error p-4"
    >
      Aufnahmen konnten nicht geladen werden.
      <UButton
        color="neutral"
        variant="link"
        @click="refreshItems()"
      >
        Erneut versuchen
      </UButton>
    </div>
    <p
      v-if="fetchStatus === 'pending'"
      role="status"
      class="text-sm text-muted"
    >
      Aufnahmen laden …
    </p>

    <section
      aria-label="Aufnahmen"
      :aria-busy="busy"
      class="space-y-3"
    >
      <div
        class="max-h-112 overflow-auto rounded-lg border border-default"
        tabindex="0"
        aria-label="Aufnahmetabelle"
      >
        <table class="w-full text-left text-sm">
          <thead class="sticky top-0 z-10 bg-muted text-muted">
            <tr>
              <th
                scope="col"
                class="p-3"
              >
                Aufnahme / Text
              </th>
              <th
                scope="col"
                class="p-3"
              >
                Datum
              </th>
              <th
                scope="col"
                class="p-3"
              >
                Quelle / Status
              </th>
              <th
                scope="col"
                class="p-3"
              >
                Notizen
              </th>
              <th
                scope="col"
                class="p-3"
              >
                <span class="sr-only">Aktion</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in items"
              :key="item.audio_id"
              class="border-t border-default"
              :class="index === currentIndex ? 'bg-primary/10' : ''"
            >
              <td class="p-3 max-w-72">
                <p
                  class="truncate font-semibold"
                  :title="item.original_filename || item.audio_file"
                >
                  {{ item.original_filename || item.audio_file }}
                </p>
                <p
                  class="truncate text-muted"
                  :title="item.transcript || item.asr_text"
                >
                  {{ item.transcript || item.asr_text || 'Kein Text' }}
                </p>
              </td>
              <td class="p-3 whitespace-nowrap">
                {{ formatDate(item.created_at) }}
              </td>
              <td class="p-3 whitespace-nowrap">
                <p>{{ sourceOptions.find(option => option.value === item.source)?.label }}</p>
                <p class="text-muted">
                  {{ statusOptions.find(option => option.value === item.status)?.label }}{{ item.unsure ? ' · Unsicher' : '' }}
                </p>
              </td>
              <td class="p-3">
                {{ item.notes || '—' }}
              </td>
              <td class="p-3">
                <UButton
                  color="neutral"
                  variant="outline"
                  :disabled="dirty || busy || Boolean(fetchError)"
                  :aria-label="`Aufnahme ${item.original_filename || item.audio_id} öffnen`"
                  @click="selectItem(index)"
                >
                  Öffnen
                </UButton>
              </td>
            </tr>
            <tr v-if="!items.length && !busy">
              <td
                colspan="5"
                class="p-5 text-center text-muted"
              >
                Keine Aufnahme in dieser Ansicht.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav
        aria-label="Seiten der Aufnahmen"
        class="flex flex-wrap items-center justify-between gap-3"
      >
        <p class="text-sm text-muted">
          {{ filteredCount }} {{ filteredCount === 1 ? 'Aufnahme' : 'Aufnahmen' }} · Seite {{ page }} von {{ pageCount }}
        </p>
        <div class="flex gap-2">
          <UButton
            color="neutral"
            variant="outline"
            :disabled="page <= 1 || dirty || busy"
            @click="page--"
          >
            Vorherige Seite
          </UButton>
          <UButton
            color="neutral"
            variant="outline"
            :disabled="page >= pageCount || dirty || busy"
            @click="page++"
          >
            Nächste Seite
          </UButton>
        </div>
      </nav>
    </section>

    <section
      v-if="current && !fetchError && fetchStatus !== 'pending'"
      ref="editor"
      class="space-y-4"
    >
      <h2 class="text-lg font-semibold">
        Aufnahme bearbeiten
      </h2>
      <div
        class="flex flex-wrap items-center gap-2 text-sm font-semibold text-muted"
      >
        <span class="rounded-md bg-muted px-2 py-1">{{
          current.source
        }}</span>
        <span>{{ current.original_filename || current.audio_file }}</span>
        <span v-if="recordedAt">· {{ recordedAt }}</span>
      </div>

      <audio
        class="w-full"
        controls
        :src="audioUrl"
      />

      <div>
        <p class="text-sm font-semibold text-muted">
          ASR-Entwurf
        </p>
        <p
          class="mt-1 min-h-12 rounded-lg border border-default bg-muted p-3 text-lg"
        >
          {{ current.asr_text || "Kein ASR-Entwurf." }}
        </p>
      </div>

      <UFormField label="Korrigierte Transkription">
        <LazyUTextarea
          v-model="transcript"
          :disabled="isSaving"
          class="w-full"
          autoresize
          size="xl"
          :rows="5"
        />
      </UFormField>

      <UCheckbox
        v-model="unsure"
        :disabled="isSaving"
        label="Unsicher"
      />

      <p
        v-if="saveError"
        role="alert"
        class="text-error"
      >
        {{ saveError }}
      </p>

      <UFormField label="Notizen">
        <LazyUTextarea
          v-model="notes"
          :disabled="isSaving"
          class="w-full"
          autoresize
          size="lg"
          :rows="3"
        />
      </UFormField>

      <div class="grid gap-3 grid-cols-3">
        <UButton
          block
          color="neutral"
          icon="i-lucide-chevron-left"
          size="lg"
          variant="ghost"
          :disabled="items.length < 2 || dirty || busy"
          @click="moveCurrent(-1)"
        >
          Zurück
        </UButton>
        <p
          class="flex items-center justify-center text-sm font-semibold text-muted"
        >
          {{ navigationLabel }}
        </p>
        <UButton
          block
          color="neutral"
          icon="i-lucide-chevron-right"
          size="lg"
          variant="ghost"
          :disabled="items.length < 2 || dirty || busy"
          @click="moveCurrent(1)"
        >
          Weiter
        </UButton>
      </div>

      <div class="grid gap-3 sm:grid-cols-3">
        <UButton
          block
          class="min-h-14"
          color="neutral"
          icon="i-lucide-skip-forward"
          size="lg"
          variant="subtle"
          :loading="isSaving"
          @click="save('skipped')"
        >
          Skip
        </UButton>
        <UButton
          block
          class="min-h-14"
          color="neutral"
          icon="i-lucide-save"
          size="lg"
          variant="outline"
          :loading="isSaving"
          @click="save('draft')"
        >
          Entwurf
        </UButton>
        <UButton
          block
          class="min-h-14"
          color="primary"
          icon="i-lucide-check"
          size="lg"
          :loading="isSaving"
          @click="save('labeled')"
        >
          Gelabelt + weiter
        </UButton>
      </div>

      <RecordingDeletion
        :recording="current"
        :disabled="isSaving || dirty"
        @deleted="refreshItems"
      />
    </section>
  </div>
</template>
