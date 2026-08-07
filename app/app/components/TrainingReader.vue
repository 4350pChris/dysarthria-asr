<script setup lang="ts">
import type { AudioQualityReport } from '~/utils/audioQuality'
import type { ReadingPrompt } from '~/types/speech'

const toast = useToast()
const prompts = ref<ReadingPrompt[]>([])
const promptIndex = ref(0)
const isLoading = ref(true)
const isSaving = ref(false)
const errorMessage = ref('')
const recordingUrl = ref('')
const recording = shallowRef<Blob>()
const audioQuality = ref<AudioQualityReport>()
const isCheckingAudio = ref(false)
const resumeVoiceCommands = ref(false)
const { checkAudio } = useAudioQualityCheck()
const speechCommands = useSpeechCommands()
const {
  isRecording,
  start: startAudioRecording,
  stop: stopAudioRecording
} = useAudioRecording({ onComplete: processRecording })

const currentPrompt = computed(() => prompts.value[promptIndex.value])
const savedCount = ref(0)
const canSaveRecording = computed(() => recording.value && !isCheckingAudio.value && audioQuality.value?.canSave !== false)

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

async function loadPrompts() {
  isLoading.value = true
  errorMessage.value = ''
  recording.value = undefined
  audioQuality.value = undefined
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = ''
  try {
    const response = await $fetch<{ prompts: ReadingPrompt[] }>('/api/training/prompts')
    prompts.value = shuffle(response.prompts)
    promptIndex.value = 0
  } catch {
    errorMessage.value = 'Die Lesetexte konnten nicht geladen werden.'
  } finally {
    isLoading.value = false
  }
}

function startRecording() {
  if (!currentPrompt.value || isRecording.value || isSaving.value) return
  errorMessage.value = ''
  resumeVoiceCommands.value = speechCommands.isListening.value
  if (resumeVoiceCommands.value) speechCommands.stop()
  void startAudioRecording().catch(() => {
    errorMessage.value = 'Das Mikrofon ist nicht verfügbar. Bitte erlaube den Mikrofonzugriff.'
    if (resumeVoiceCommands.value) {
      resumeVoiceCommands.value = false
      speechCommands.start()
    }
  })
}

function stopRecording() {
  stopAudioRecording()
}

async function processRecording(audio: Blob) {
  recording.value = audio
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = URL.createObjectURL(audio)
  isCheckingAudio.value = true
  try {
    audioQuality.value = await checkAudio(audio)
  } catch {
    audioQuality.value = {
      canSave: true,
      issues: [{
        code: 'quiet',
        level: 'warning',
        message: 'Die Audio-Prüfung ist nicht verfügbar. Höre die Aufnahme vor dem Speichern an.'
      }]
    }
  } finally {
    isCheckingAudio.value = false
    if (resumeVoiceCommands.value) {
      resumeVoiceCommands.value = false
      speechCommands.start()
    }
  }
}

useSpeechCommand({
  id: 'training-record',
  label: 'Aufnehmen',
  phrases: ['aufnehmen', 'aufnahme', 'start', 'los'],
  handler: startRecording
})
useSpeechCommand({
  id: 'training-retry',
  label: 'Neu aufnehmen',
  phrases: ['neu aufnehmen', 'nochmal', 'wiederholen'],
  handler: discardRecording
})
useSpeechCommand({
  id: 'training-save',
  label: 'Speichern',
  phrases: ['speichern', 'aufnahme speichern', 'weiter'],
  handler: saveRecording
})

function discardRecording() {
  recording.value = undefined
  audioQuality.value = undefined
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = ''
}

async function saveRecording() {
  const audio = recording.value
  if (!audio || !canSaveRecording.value || !currentPrompt.value || isSaving.value) return
  isSaving.value = true
  errorMessage.value = ''
  const form = new FormData()
  form.append('prompt_id', currentPrompt.value.id)
  form.append('audio', audio, 'guided-reading.webm')
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
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
})

onMounted(async () => {
  try {
    await loadPrompts()
  } catch {
    errorMessage.value = 'Die Lesetexte konnten nicht geladen werden.'
    isLoading.value = false
  }
})
</script>

<template>
  <section class="space-y-5">
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

      <RecordControl
        v-if="!recording"
        :is-busy="isSaving"
        :is-recording="isRecording"
        @start="startRecording"
        @stop="stopRecording"
      >
        <template #default="{ isBusy, isRecording: recordingActive, toggle }">
          <UButton
            block
            class="min-h-28 justify-center rounded-3xl text-xl font-extrabold"
            :color="recordingActive ? 'error' : 'primary'"
            :disabled="isBusy"
            :icon="recordingActive ? 'i-lucide-square' : 'i-lucide-mic'"
            size="xl"
            @click="toggle"
          >
            {{ recordingActive ? 'Aufnahme stoppen' : 'Diesen Text aufnehmen' }}
          </UButton>
        </template>
      </RecordControl>

      <template v-else>
        <audio
          class="w-full"
          controls
          :src="recordingUrl"
        />
        <UAlert
          v-if="isCheckingAudio"
          color="info"
          icon="i-lucide-audio-lines"
          title="Aufnahme wird geprüft"
          description="Bitte warte kurz."
        />
        <UAlert
          v-else-if="audioQuality?.issues.length"
          :color="audioQuality.canSave ? 'warning' : 'error'"
          icon="i-lucide-circle-alert"
          title="Aufnahme prüfen"
          :description="audioQuality.issues.map(issue => issue.message).join(' ')"
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
            :disabled="!canSaveRecording"
            :loading="isSaving || isCheckingAudio"
            @click="saveRecording"
          >
            Als Trainingspaar speichern
          </UButton>
        </div>
      </template>
    </template>
  </section>
</template>
