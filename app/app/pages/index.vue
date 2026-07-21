<script setup lang="ts">
import type { Phrase, Suggestion, TranscriptionResult } from '~/types/speech'

const route = useRoute()

const recorder = shallowRef<MediaRecorder>()
const chunks = ref<Blob[]>([])
const result = ref<TranscriptionResult>()
const selected = ref<Suggestion>()
const status = ref('')
const isRecording = ref(false)
const isBusy = ref(false)
const isSaving = ref(false)
const hasSaved = ref(false)
const shouldResumeVoiceCommands = ref(false)

const suggestions = computed(() => result.value?.suggestions ?? [])
const hasSelection = computed(() => Boolean(selected.value))
const selectedIndex = computed(() => suggestions.value.findIndex(suggestion => suggestion.phrase_id === selected.value?.phrase_id))

onMounted(selectRoutePhrase)

const voiceCommands = useVoiceCommands(handleVoiceCommand)
const silenceDetection = useSilenceDetection(stopRecording)

function setSelection(suggestion: Suggestion) {
  selected.value = suggestion
}

function selectSuggestionAt(index: number) {
  if (!suggestions.value.length) return
  const nextIndex = (index + suggestions.value.length) % suggestions.value.length
  selected.value = suggestions.value[nextIndex]
  status.value = 'Vorschlag gewechselt.'
}

function selectPhrase(phrase: Phrase) {
  result.value = undefined
  selected.value = {
    phrase_id: phrase.id,
    text: phrase.text,
    score: 1
  }
  hasSaved.value = false
  status.value = 'Direkt ausgewählt.'
}

async function selectRoutePhrase() {
  const phraseId = Number(route.query.phrase || 0)
  if (!phraseId) return
  try {
    const { byId } = await usePhrases()
    const phrase = byId(phraseId)
    if (phrase) selectPhrase(phrase)
  } catch {
    status.value = 'Phrase konnte nicht geladen werden.'
  }
}

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  chunks.value = []
  result.value = undefined
  selected.value = undefined
  hasSaved.value = false
  status.value = ''
  recorder.value = new MediaRecorder(stream)
  recorder.value.ondataavailable = event => chunks.value.push(event.data)
  recorder.value.onstop = async () => {
    silenceDetection.stop()
    stream.getTracks().forEach(track => track.stop())
    await transcribe(new Blob(chunks.value, { type: recorder.value?.mimeType || 'audio/webm' }))
  }
  recorder.value.start()
  silenceDetection.start(stream)
  isRecording.value = true
  status.value = 'Aufnahme läuft...'
}

function stopRecording() {
  if (!recorder.value || recorder.value.state === 'inactive') return
  isRecording.value = false
  isBusy.value = true
  status.value = 'Ich höre zu...'
  recorder.value.stop()
}

function speakHelp() {
  speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance('Sag aufnehmen, stopp, vorlesen, weiter, zurück oder hilfe.')
  utterance.lang = 'de-DE'
  speechSynthesis.speak(utterance)
}

function handleVoiceCommand(command: 'start' | 'stop' | 'speak' | 'next' | 'previous' | 'help') {
  if (command === 'start' && !isRecording.value && !isBusy.value) {
    shouldResumeVoiceCommands.value = voiceCommands.isListening.value
    voiceCommands.stop()
    void startRecording()
  } else if (command === 'stop' && isRecording.value) {
    stopRecording()
  } else if (command === 'speak' && selected.value) {
    submit()
  } else if (command === 'next') {
    selectSuggestionAt(selectedIndex.value + 1)
  } else if (command === 'previous') {
    selectSuggestionAt(selectedIndex.value - 1)
  } else if (command === 'help') {
    speakHelp()
  }
}

async function transcribe(blob: Blob) {
  const form = new FormData()
  form.append('audio', blob, 'recording.webm')

  try {
    const response = await fetch('/api/transcribe', { method: 'POST', body: form })
    if (!response.ok) throw new Error('Erkennung fehlgeschlagen.')
    result.value = await response.json()
    selected.value = result.value?.suggestions[0]
    hasSaved.value = false
    status.value = selected.value ? 'Meinst du das?' : 'Kein Vorschlag gefunden.'
  } catch (error) {
    status.value = error instanceof Error ? error.message : 'Erkennung fehlgeschlagen.'
  } finally {
    isBusy.value = false
    if (shouldResumeVoiceCommands.value) {
      shouldResumeVoiceCommands.value = false
      voiceCommands.start()
    }
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
  if (!result.value || !selected.value || hasSaved.value || isSaving.value) return
  isSaving.value = true
  const top = result.value.suggestions[0]
  const form = new FormData()
  form.append('audio_id', result.value.audio_id)
  form.append('source', 'friend_app')
  form.append('phrase_id', String(selected.value.phrase_id))
  form.append('expected_text', selected.value.text)
  form.append('raw_transcript', result.value.raw_transcript)
  form.append('corrected_text', selected.value.text)
  form.append('suggested_phrase_id', top?.phrase_id ? String(top.phrase_id) : '')
  form.append('suggested_text', top?.text || '')
  form.append('suggestion_score', top?.score ? String(top.score) : '')
  form.append('was_understandable', 'true')
  try {
    await fetch('/api/speech-attempts', { method: 'POST', body: form })
    hasSaved.value = true
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <UMain class="min-h-dvh bg-slate-50 px-4 py-5 text-slate-950">
    <UContainer class="flex min-h-[calc(100dvh-2.5rem)] max-w-md flex-col">
      <SpeakerHeader />

      <UForm
        :state="{}"
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

        <VoiceCommandControl
          :is-listening="voiceCommands.isListening.value"
          :is-supported="voiceCommands.isSupported.value"
          :status="voiceCommands.status.value"
          @start="voiceCommands.start"
          @stop="voiceCommands.stop"
        />

        <section
          v-if="hasSelection"
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

        <UButton
          class="min-h-24 justify-center rounded-2xl text-xl font-extrabold"
          block
          color="neutral"
          icon="i-lucide-layout-grid"
          size="xl"
          to="/phrases"
          variant="subtle"
          :ui="{ leadingIcon: 'size-8', base: 'flex-col gap-2' }"
        >
          Satz auswählen
        </UButton>
      </UForm>
    </UContainer>
  </UMain>
</template>
