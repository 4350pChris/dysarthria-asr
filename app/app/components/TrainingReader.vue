<script setup lang="ts">
import type { TrainingPrompt } from '~/types/speech'

const toast = useToast()
const topics = ref<string[]>([])
const selectedTopic = ref('')
const prompts = ref<TrainingPrompt[]>([])
const promptIndex = ref(0)
const isLoading = ref(true)
const isRecording = ref(false)
const isSaving = ref(false)
const consented = ref(false)
const errorMessage = ref('')
const recorder = shallowRef<MediaRecorder>()
const chunks = ref<Blob[]>([])
const stream = shallowRef<MediaStream>()
const recordingUrl = ref('')
const recording = shallowRef<Blob>()

const topicOptions = computed(() => topics.value.map(topic => ({
  label: topic === 'Tatoeba CC0' ? 'Freie Beispielsätze' : topic,
  value: topic
})))
const currentPrompt = computed(() => prompts.value[promptIndex.value])
const savedCount = ref(0)
const tatoebaImported = ref(0)
const isImportingTatoeba = ref(false)

function shuffle<T>(items: T[]): T[] {
  const copy = [...items]
  for (let index = copy.length - 1; index > 0; index--) {
    const replacement = Math.floor(Math.random() * (index + 1))
    const selected = copy[index]!
    copy[index] = copy[replacement]!
    copy[replacement] = selected
  }
  return copy
}

async function loadPrompts(topic: string) {
  isLoading.value = true
  errorMessage.value = ''
  recording.value = undefined
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = ''
  try {
    const response = await $fetch<{ prompts: TrainingPrompt[] }>('/api/training/prompts', { query: { topic } })
    prompts.value = shuffle(response.prompts)
    promptIndex.value = 0
  } catch {
    errorMessage.value = 'Die Lesetexte konnten nicht geladen werden.'
  } finally {
    isLoading.value = false
  }
}

async function selectTopic(topic: string) {
  if (!topic || isRecording.value || isSaving.value) return
  selectedTopic.value = topic
  await loadPrompts(topic)
}

async function importTatoeba() {
  if (isImportingTatoeba.value || isRecording.value || isSaving.value) return
  isImportingTatoeba.value = true
  errorMessage.value = ''
  try {
    const response = await $fetch<{ imported: number, topic: string }>('/api/training/tatoeba/import', { method: 'POST' })
    tatoebaImported.value = response.imported
    if (!topics.value.includes(response.topic)) topics.value.push(response.topic)
    await selectTopic(response.topic)
    toast.add({ title: 'Beispielsätze geladen', description: `${response.imported} kurze deutsche Sätze sind lokal verfügbar.`, color: 'success', icon: 'i-lucide-download-check' })
  } catch {
    errorMessage.value = 'Die Beispielsätze konnten nicht geladen werden. Bitte überprüfe die Internetverbindung und versuche es erneut.'
  } finally {
    isImportingTatoeba.value = false
  }
}

async function startRecording() {
  if (!consented.value || !currentPrompt.value || isRecording.value || isSaving.value) return
  errorMessage.value = ''
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks.value = []
    recorder.value = new MediaRecorder(stream.value)
    recorder.value.ondataavailable = event => chunks.value.push(event.data)
    recorder.value.onstop = () => {
      stream.value?.getTracks().forEach(track => track.stop())
      stream.value = undefined
      recording.value = new Blob(chunks.value, { type: recorder.value?.mimeType || 'audio/webm' })
      if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
      recordingUrl.value = URL.createObjectURL(recording.value)
      isRecording.value = false
    }
    recorder.value.start()
    isRecording.value = true
  } catch {
    errorMessage.value = 'Das Mikrofon ist nicht verfügbar. Bitte erlaube den Mikrofonzugriff.'
  }
}

function stopRecording() {
  if (recorder.value?.state === 'recording') recorder.value.stop()
}

function discardRecording() {
  recording.value = undefined
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = ''
}

async function saveRecording() {
  if (!recording.value || !currentPrompt.value || isSaving.value) return
  isSaving.value = true
  errorMessage.value = ''
  const form = new FormData()
  form.append('prompt_id', currentPrompt.value.id)
  form.append('audio', recording.value, 'guided-reading.webm')
  try {
    await $fetch('/api/training/recordings', { method: 'POST', body: form })
    savedCount.value += 1
    discardRecording()
    promptIndex.value = (promptIndex.value + 1) % prompts.value.length
    toast.add({ title: 'Aufnahme gespeichert', description: 'Text und Audio sind direkt als Trainingspaar markiert.', color: 'success', icon: 'i-lucide-check-circle' })
  } catch {
    errorMessage.value = 'Die Aufnahme konnte nicht gespeichert werden. Bitte versuche es noch einmal.'
  } finally {
    isSaving.value = false
  }
}

onBeforeUnmount(() => {
  stream.value?.getTracks().forEach(track => track.stop())
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
})

onMounted(async () => {
  try {
    const response = await $fetch<{ topics: string[] }>('/api/training/topics')
    topics.value = response.topics
    tatoebaImported.value = (await $fetch<{ imported: number }>('/api/training/tatoeba')).imported
    selectedTopic.value = topics.value[0] || ''
    if (selectedTopic.value) await loadPrompts(selectedTopic.value)
  } catch {
    errorMessage.value = 'Die Lesetexte konnten nicht geladen werden.'
    isLoading.value = false
  }
})
</script>

<template>
  <section class="space-y-5">
    <UAlert
      color="info"
      icon="i-lucide-shield-check"
      title="Aufnahmen bleiben lokal"
      description="Jede Aufnahme wird mit dem angezeigten Text gespeichert und ist sofort für den lokalen Trainingsexport bereit."
    />

    <UFormField
      label="Thema"
      description="Originale Übungstexte oder lokal importierte freie Beispielsätze."
    >
      <USelect
        v-model="selectedTopic"
        class="w-full"
        :items="topicOptions"
        size="xl"
        :disabled="isLoading || isRecording || isSaving"
        @update:model-value="selectTopic"
      />
    </UFormField>

    <UAlert
      color="neutral"
      icon="i-lucide-database"
      title="Freie Beispielsätze"
      :description="tatoebaImported ? `${tatoebaImported} kurze deutsche Sätze sind lokal gespeichert.` : 'Lädt einmalig eine Sammlung kurzer deutscher Sätze in die lokale Datenablage.'"
    >
      <template #actions>
        <UButton
          color="neutral"
          icon="i-lucide-download"
          :loading="isImportingTatoeba"
          :disabled="isRecording || isSaving"
          size="lg"
          @click="importTatoeba"
        >
          {{ tatoebaImported ? 'Aktualisieren' : 'Beispielsätze laden' }}
        </UButton>
      </template>
    </UAlert>

    <UAlert
      v-if="errorMessage"
      color="error"
      icon="i-lucide-circle-alert"
      :description="errorMessage"
    />

    <div
      v-if="isLoading"
      class="space-y-3"
    >
      <USkeleton class="h-8 w-24" />
      <USkeleton class="h-36 w-full" />
    </div>

    <template v-else-if="currentPrompt">
      <div class="flex items-center justify-between gap-3 text-sm font-semibold text-muted">
        <span>Text {{ promptIndex + 1 }} von {{ prompts.length }}</span>
        <span v-if="savedCount">{{ savedCount }} gespeichert</span>
      </div>

      <UCard :ui="{ body: 'p-6 sm:p-8' }">
        <p class="text-2xl leading-relaxed font-semibold text-highlighted sm:text-3xl">
          {{ currentPrompt.text }}
        </p>
      </UCard>

      <UCheckbox
        v-model="consented"
        size="lg"
        label="Ich möchte diese Aufnahme als Trainingsdaten lokal speichern."
      />

      <UButton
        v-if="!recording"
        block
        class="min-h-28 justify-center rounded-3xl text-xl font-extrabold"
        :color="isRecording ? 'error' : 'primary'"
        :disabled="!consented || isSaving"
        :icon="isRecording ? 'i-lucide-square' : 'i-lucide-mic'"
        size="xl"
        @click="isRecording ? stopRecording() : startRecording()"
      >
        {{ isRecording ? 'Aufnahme stoppen' : 'Diesen Text aufnehmen' }}
      </UButton>

      <template v-else>
        <audio
          class="w-full"
          controls
          :src="recordingUrl"
        />
        <div class="grid grid-cols-2 gap-3">
          <UButton
            block
            color="neutral"
            icon="i-lucide-rotate-ccw"
            size="xl"
            variant="soft"
            :disabled="isSaving"
            @click="discardRecording"
          >
            Neu aufnehmen
          </UButton>
          <UButton
            block
            color="primary"
            icon="i-lucide-save"
            size="xl"
            :loading="isSaving"
            @click="saveRecording"
          >
            Als Trainingspaar speichern
          </UButton>
        </div>
      </template>
    </template>
  </section>
</template>
