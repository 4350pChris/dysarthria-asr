<script setup lang="ts">
import type { AudioSource, LabelItem, LabelStatus } from '~/types/speech'

definePageMeta({
  pageHeader: {
    action: {
      icon: 'i-lucide-package-down',
      label: 'Training-ZIP',
      to: '/api/labeling/training-data.zip'
    },
    eyebrow: 'Audio-Labels',
    showBack: true,
    title: 'Aufnahmen prüfen',
    wide: true
  }
})

type ItemsResponse = {
  items: LabelItem[]
  filtered_count: number
  counts: Record<LabelStatus | 'total', number>
}

const sourceOptions = [
  { label: 'Alle Quellen', value: 'all' },
  { label: 'App-Aufnahmen', value: 'app_recording' },
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
const statusFilter = ref<LabelStatus | 'all'>('draft')
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
  ...(sourceFilter.value !== 'all' ? { source: sourceFilter.value } : {}),
  ...(statusFilter.value !== 'all' ? { status: statusFilter.value } : {}),
  ...(unsureOnly.value ? { unsure: true } : {}),
  ...(missingAsrOnly.value ? { missing_asr: true } : {})
}))

const {
  data: itemsData,
  refresh: refreshItems
} = await useFetch<ItemsResponse>('/api/labeling/items', {
  query: itemsQuery,
  default: () => ({ items: [], filtered_count: 0, counts: emptyCounts })
})

const items = computed(() => itemsData.value.items)
const filteredCount = computed(() => itemsData.value.filtered_count)
const counts = computed(() => itemsData.value.counts)
const current = computed(() => items.value[currentIndex.value])
const audioUrl = computed(() =>
  current.value ? `/api/labeling/audio/${current.value.audio_id}` : ''
)

watch(
  current,
  (item) => {
    transcript.value = item?.transcript || item?.asr_text || ''
    notes.value = item?.notes || ''
    unsure.value = Boolean(item?.unsure)
  },
  { immediate: true }
)

watch([sourceFilter, statusFilter, unsureOnly, missingAsrOnly], () => {
  currentIndex.value = 0
})

watch(items, (nextItems) => {
  if (currentIndex.value >= nextItems.length) currentIndex.value = 0
})

async function save(nextStatus: LabelStatus) {
  if (!current.value || isSaving.value) return
  isSaving.value = true
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
    if (currentIndex.value < items.value.length - 1) currentIndex.value += 1
    else currentIndex.value = 0
  } finally {
    isSaving.value = false
  }
}

function moveCurrent(delta: number) {
  if (!items.value.length) return
  currentIndex.value
    = (currentIndex.value + delta + items.value.length) % items.value.length
}
</script>

<template>
  <div class="space-y-5">
    <UButton
      class="font-extrabold"
      color="neutral"
      icon="i-lucide-upload"
      size="lg"
      to="/whatsapp-import"
    >
      WhatsApp-Audios importieren
    </UButton>

    <section class="grid gap-3 sm:grid-cols-4">
      <UFormField label="Quelle">
        <USelect
          v-model="sourceFilter"
          class="w-full"
          :items="sourceOptions"
          size="lg"
        />
      </UFormField>
      <UFormField label="Status">
        <USelect
          v-model="statusFilter"
          class="w-full"
          :items="statusOptions"
          size="lg"
        />
      </UFormField>
      <UCheckbox
        v-model="unsureOnly"
        class="min-h-16 items-center"
        label="Nur unsichere"
        size="lg"
      />
      <UCheckbox
        v-model="missingAsrOnly"
        class="min-h-16 items-center"
        label="Ohne ASR-Text"
        size="lg"
      />
    </section>

    <p class="text-sm font-semibold text-muted">
      {{ counts.draft }} offen · {{ counts.labeled }} gelabelt ·
      {{ counts.skipped }} übersprungen
    </p>

    <EmptyAsrBulkDeletion
      v-if="missingAsrOnly"
      :count="filteredCount"
      :source="sourceFilter"
      :status="statusFilter"
      :unsure-only="unsureOnly"
      @deleted="refreshItems"
    />

    <section
      v-if="current"
      class="space-y-4"
    >
      <div
        class="flex flex-wrap items-center gap-2 text-sm font-semibold text-muted"
      >
        <span class="rounded-md bg-muted px-2 py-1">{{
          current.source
        }}</span>
        <span>{{ current.original_filename || current.audio_file }}</span>
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
          class="w-full"
          autofocus
          autoresize
          size="xl"
          :rows="5"
        />
      </UFormField>

      <UCheckbox
        v-model="unsure"
        label="Unsicher"
      />

      <UFormField label="Notizen">
        <LazyUTextarea
          v-model="notes"
          class="w-full"
          autoresize
          size="lg"
          :rows="3"
        />
      </UFormField>

      <div class="grid gap-3 grid-cols-3">
        <UButton
          block
          class="font-extrabold"
          color="neutral"
          icon="i-lucide-chevron-left"
          size="lg"
          variant="ghost"
          :disabled="items.length < 2"
          @click="moveCurrent(-1)"
        >
          Zurück
        </UButton>
        <p
          class="flex items-center justify-center text-sm font-semibold text-muted"
        >
          {{ currentIndex + 1 }} / {{ items.length }}
        </p>
        <UButton
          block
          class="font-extrabold"
          color="neutral"
          icon="i-lucide-chevron-right"
          size="lg"
          variant="ghost"
          :disabled="items.length < 2"
          @click="moveCurrent(1)"
        >
          Weiter
        </UButton>
      </div>

      <div class="grid gap-3 sm:grid-cols-3">
        <UButton
          block
          class="min-h-14 justify-center font-extrabold"
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
          class="min-h-14 justify-center font-extrabold"
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
          class="min-h-14 justify-center font-extrabold"
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
        :disabled="isSaving"
        @deleted="refreshItems"
      />
    </section>

    <p
      v-else
      class="rounded-lg border border-default p-5 text-center text-lg font-semibold text-muted"
    >
      Keine Aufnahme in dieser Ansicht.
    </p>
  </div>
</template>
