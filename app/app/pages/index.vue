<script setup lang="ts">
import type { Suggestion, TranscriptionResult } from '~/types/speech'

const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const formState = reactive({})
const recorder = shallowRef<MediaRecorder>()
const chunks = ref<Blob[]>([])
const result = ref<TranscriptionResult>()
const selected = ref<Suggestion>()
const status = ref('')
const isRecording = ref(false)
const isBusy = ref(false)

const suggestions = computed(() => result.value?.suggestions ?? [])
const hasResult = computed(() => Boolean(result.value))

function setSelection(suggestion: Suggestion) {
  selected.value = suggestion
}

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  chunks.value = []
  result.value = undefined
  selected.value = undefined
  status.value = ''
  recorder.value = new MediaRecorder(stream)
  recorder.value.ondataavailable = event => chunks.value.push(event.data)
  recorder.value.onstop = async () => {
    stream.getTracks().forEach(track => track.stop())
    await transcribe(new Blob(chunks.value, { type: recorder.value?.mimeType || 'audio/webm' }))
  }
  recorder.value.start()
  isRecording.value = true
}

function stopRecording() {
  if (!recorder.value || recorder.value.state === 'inactive') return
  isRecording.value = false
  isBusy.value = true
  status.value = 'Ich höre zu...'
  recorder.value.stop()
}

async function transcribe(blob: Blob) {
  const form = new FormData()
  form.append('audio', blob, 'recording.webm')

  try {
    const response = await fetch(`${apiBase}/api/transcribe`, { method: 'POST', body: form })
    if (!response.ok) throw new Error('Erkennung fehlgeschlagen.')
    result.value = await response.json()
    selected.value = result.value?.suggestions[0]
    status.value = selected.value ? 'Meinst du das?' : 'Kein Vorschlag gefunden.'
  } catch (error) {
    status.value = error instanceof Error ? error.message : 'Erkennung fehlgeschlagen.'
  } finally {
    isBusy.value = false
  }
}

function submit() {
  const text = selected.value?.text
  if (!text) return
  speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'de-DE'
  speechSynthesis.speak(utterance)
  void saveAttempt()
}

async function saveAttempt() {
  if (!result.value || !selected.value) return
  const top = result.value.suggestions[0]
  const form = new FormData()
  form.append('audio_id', result.value.audio_id)
  form.append('audio_path', result.value.audio_path)
  form.append('source', 'friend_app')
  form.append('phrase_number', selected.value.phrase_number)
  form.append('expected_text', selected.value.text)
  form.append('raw_transcript', result.value.raw_transcript)
  form.append('corrected_text', selected.value.text)
  form.append('suggested_phrase_number', top?.phrase_number || '')
  form.append('suggested_text', top?.text || '')
  form.append('suggestion_score', top?.score ? String(top.score) : '')
  form.append('was_understandable', 'true')
  await fetch(`${apiBase}/api/corrections`, { method: 'POST', body: form })
}
</script>

<template>
  <UMain class="min-h-dvh bg-slate-50 px-4 py-5 text-slate-950">
    <UContainer class="flex min-h-[calc(100dvh-2.5rem)] max-w-md flex-col">
      <SpeakerHeader />

      <UForm
        :state="formState"
        class="flex flex-1 flex-col justify-start gap-5"
        @submit="submit"
      >
        <RecordControl
          :is-recording="isRecording"
          :is-busy="isBusy"
          @start="startRecording"
          @stop="stopRecording"
        />

        <p class="min-h-7 text-center text-lg font-semibold text-slate-600">
          {{ status }}
        </p>

        <section
          v-if="hasResult"
          class="space-y-4"
        >
          <MatchedPhrase
            :selected="selected"
          />

          <SuggestionList
            :suggestions="suggestions"
            :selected="selected"
            @select="setSelection"
          />
        </section>
      </UForm>
    </UContainer>
  </UMain>
</template>
