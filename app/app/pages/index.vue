<script setup lang="ts">
const route = useRoute()

const shouldResumeVoiceCommands = ref(false)
const mode = ref<'phrases' | 'math'>('phrases')
const modeOptions = [
  { label: 'Sätze', value: 'phrases' },
  { label: 'Mathe', value: 'math' }
]
const speech = useSpeechSession(mode)
const { byId, loadPhrases } = usePhrases()

onMounted(selectRoutePhrase)

const voiceCommands = useVoiceCommands(handleVoiceCommand)

async function selectRoutePhrase() {
  const phraseId = Number(route.query.phrase || 0)
  if (!phraseId) return
  try {
    await loadPhrases()
    const phrase = byId(phraseId)
    if (phrase) speech.selectPhrase(phrase)
  } catch {
    speech.status.value = 'Phrase konnte nicht geladen werden.'
  }
}

function speakHelp() {
  speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(
    'Sag aufnehmen. Sprich deinen Satz. Ich stoppe automatisch, wenn es ruhig ist. Danach sag vorlesen, kopieren oder teilen. Sag Mathe für den Mathemodus. Sag Sätze für den Satzmodus. Sag weiter für den nächsten Vorschlag. Sag zurück für den vorherigen Vorschlag.'
  )
  utterance.lang = 'de-DE'
  speechSynthesis.speak(utterance)
}

function handleVoiceCommand(command: 'start' | 'stop' | 'speak' | 'copy' | 'share' | 'phrasesMode' | 'mathMode' | 'next' | 'previous' | 'help') {
  if (command === 'start' && !speech.isRecording.value && !speech.isBusy.value) {
    shouldResumeVoiceCommands.value = voiceCommands.isListening.value
    voiceCommands.stop()
    void speech.startRecording().finally(resumeVoiceCommands)
  } else if (command === 'stop' && speech.isRecording.value) {
    speech.stopRecording()
  } else if (command === 'speak' && (speech.selected.value || speech.result.value?.math_text)) {
    submit()
  } else if (command === 'copy' && speech.outputText.value) {
    void speech.copySelected()
  } else if (command === 'share' && speech.outputText.value) {
    void speech.shareSelected()
  } else if (command === 'phrasesMode') {
    mode.value = 'phrases'
    speech.status.value = 'Satzmodus.'
  } else if (command === 'mathMode') {
    mode.value = 'math'
    speech.status.value = 'Mathemodus.'
  } else if (command === 'next') {
    speech.selectSuggestionAt(speech.selectedIndex.value + 1)
  } else if (command === 'previous') {
    speech.selectSuggestionAt(speech.selectedIndex.value - 1)
  } else if (command === 'help') {
    speakHelp()
  }
}

function resumeVoiceCommands() {
  if (!shouldResumeVoiceCommands.value) return
  shouldResumeVoiceCommands.value = false
  voiceCommands.start()
}

function submit() {
  speech.speakSelected()
}
</script>

<template>
  <UMain class="min-h-dvh bg-default px-4 py-5 text-highlighted">
    <UContainer class="flex min-h-[calc(100dvh-2.5rem)] max-w-md flex-col">
      <SpeakerHeader />

      <UForm
        :state="{}"
        class="flex flex-1 flex-col justify-start gap-5"
        @submit="submit"
      >
        <RecordControl
          :is-recording="speech.isRecording.value"
          :is-busy="speech.isBusy.value"
          @start="speech.startRecording"
          @stop="speech.stopRecording"
        />

        <URadioGroup
          v-model="mode"
          class="w-full"
          color="primary"
          indicator="hidden"
          :items="modeOptions"
          legend="Modus"
          orientation="horizontal"
          size="xl"
          variant="table"
          :ui="{
            legend: 'sr-only',
            fieldset: 'w-full',
            item: 'min-h-16 flex-1 items-center justify-center',
            label: 'text-lg font-extrabold'
          }"
        />

        <p class="min-h-7 text-center text-lg font-semibold text-toned">
          {{ speech.status.value }}
        </p>

        <VoiceCommandControl
          :is-listening="voiceCommands.isListening.value"
          :is-supported="voiceCommands.isSupported.value"
          :status="voiceCommands.status.value"
          @start="voiceCommands.start"
          @stop="voiceCommands.stop"
        />

        <section
          v-if="speech.hasSelection.value && mode === 'phrases'"
          class="space-y-4"
        >
          <MatchedPhrase
            :selected="speech.selected.value"
            @copy="speech.copySelected"
            @share="speech.shareSelected"
          />

          <SuggestionList
            :suggestions="speech.suggestions.value"
            :selected="speech.selected.value"
            @select="speech.setSelection"
          />
        </section>

        <MathResult
          v-if="speech.hasMathResult.value && speech.result.value"
          :math-text="speech.result.value.math_text"
          :corrected-text="speech.result.value.math_corrected_text"
          @copy="speech.copySelected"
          @share="speech.shareSelected"
        />

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
