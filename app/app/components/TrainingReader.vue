<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { AudioQualityReport } from '~/utils/audioQuality'
import type { ReadingPrompt } from '~/types/speech'

type TrainingRecordingFormState = { promptId: string }

const toast = useToast()
const { data: promptResponse, error: promptError } = await useFetch<{ prompts: ReadingPrompt[] }>('/api/training/prompts', {
  default: () => ({ prompts: [] })
})
const prompts = computed(() => promptResponse.value.prompts)
const promptIndex = ref(0)
const errorMessage = ref(promptError.value ? apiErrorMessage(promptError.value, 'Die Lesetexte konnten nicht geladen werden.') : '')
const formState = reactive<TrainingRecordingFormState>({ promptId: '' })
const reviewForm = useTemplateRef('reviewForm')
const recordingUrl = ref('')
const recording = shallowRef<Blob>()
const audioQuality = ref<AudioQualityReport>()
const resumeVoiceCommands = ref(false)
const { checkAudio } = useAudioQualityCheck()
const speechCommands = useSpeechCommands()
const { clearErrors, formErrors, isSaving, submit }
  = useFormSubmission<TrainingRecordingFormState>('Die Aufnahme konnte nicht gespeichert werden.')
const {
  isRecording,
  start: startAudioRecording,
  stop: stopAudioRecording
} = useAudioRecording({ onComplete: processRecording })

const currentPrompt = computed(() => prompts.value[promptIndex.value])
const savedCount = ref(0)
const canSaveRecording = computed(() => Boolean(recording.value) && audioQuality.value?.canSave !== false)

watch(currentPrompt, (prompt) => {
  formState.promptId = prompt?.id || ''
}, { immediate: true })

function startRecording() {
  if (!currentPrompt.value || isRecording.value || isSaving.value) return
  clearErrors()
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
  clearErrors()
  recording.value = audio
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = URL.createObjectURL(audio)
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
  handler: () => reviewForm.value?.submit()
})
function discardRecording() {
  clearErrors()
  recording.value = undefined
  audioQuality.value = undefined
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
  recordingUrl.value = ''
}

async function saveRecording(event: FormSubmitEvent<TrainingRecordingFormState>) {
  const audio = recording.value
  if (!audio || !canSaveRecording.value || !currentPrompt.value || isSaving.value) return
  const form = new FormData()
  form.append('audio', audio, 'guided-reading.webm')
  const saved = await submit(event, (data) => {
    form.append('prompt_id', data.promptId)
    return $fetch('/api/training/recordings', { method: 'POST', body: form })
  })
  if (!saved) return
  savedCount.value += 1
  discardRecording()
  promptIndex.value = (promptIndex.value + 1) % prompts.value.length
  toast.add({
    title: 'Gespeichert',
    description: 'Eine Aufnahme mehr für deine Sprachhilfe.',
    color: 'success',
    icon: 'i-lucide-check-circle'
  })
}

onBeforeUnmount(() => {
  if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
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

    <template v-if="currentPrompt">
      <TrainingPrompt
        :index="promptIndex"
        :saved-count="savedCount"
        :text="currentPrompt.text"
        :total="prompts.length"
      />

      <TrainingRecordControl
        v-if="!recording"
        :is-busy="isSaving"
        :is-recording="isRecording"
        @start="startRecording"
        @stop="stopRecording"
      />

      <UForm
        v-else
        ref="reviewForm"
        :state="formState"
        @submit="saveRecording"
      >
        <UFormField :error="formErrors.prompt_id || formErrors.audio || formErrors._form">
          <TrainingRecordingReview
            :audio-quality="audioQuality"
            :can-save="canSaveRecording"
            :is-saving="isSaving"
            :recording-url="recordingUrl"
            @retry="discardRecording"
          />
        </UFormField>
      </UForm>

      <TrainingProgress :saved-count="savedCount" />
    </template>
  </section>
</template>
