<script setup lang="ts">
const route = useRoute()

definePageMeta({
  pageHeader: {
    eyebrow: 'Sprachhilfe',
    title: 'Was möchtest du sagen?'
  }
})

const mode = ref<'phrases' | 'math'>('phrases')
const modeOptions = [
  { label: 'Sätze', value: 'phrases' },
  { label: 'Mathe', value: 'math' }
]
const speech = useSpeechSession(mode)
const { byId, ready } = usePhrases()
const speechCommands = useSpeechCommands()

await selectRoutePhrase()
useSpeechCommand({ id: 'record', label: 'Aufnehmen', phrases: ['aufnehmen', 'aufnahme', 'start', 'los'], handler: startRecording })
useSpeechCommand({ id: 'stop-recording', label: 'Stopp', phrases: ['stopp', 'stop', 'anhalten', 'fertig'], handler: speech.stopRecording })
useSpeechCommand({ id: 'speak', label: 'Vorlesen', phrases: ['vorlesen', 'sagen', 'sprich', 'sprechen'], handler: submit })
useSpeechCommand({ id: 'copy', label: 'Kopieren', phrases: ['kopieren', 'kopie', 'abschreiben'], handler: speech.copySelected })
useSpeechCommand({ id: 'share', label: 'Teilen', phrases: ['teilen', 'senden', 'schicken', 'whatsapp', 'verschicken'], handler: speech.shareSelected })
useSpeechCommand({
  id: 'phrases-mode',
  label: 'Satzmodus',
  phrases: ['sätze', 'satzmodus', 'sätze modus'],
  handler: () => {
    mode.value = 'phrases'
    speech.status.value = 'Satzmodus.'
  }
})
useSpeechCommand({
  id: 'math-mode',
  label: 'Mathemodus',
  phrases: ['mathe', 'mathemodus'],
  handler: () => {
    mode.value = 'math'
    speech.status.value = 'Mathemodus.'
  }
})
useSpeechCommand({ id: 'next', label: 'Nächster Vorschlag', phrases: ['weiter', 'nächster', 'nächste', 'nein'], handler: () => speech.selectSuggestionAt(speech.selectedIndex.value + 1) })
useSpeechCommand({ id: 'previous', label: 'Vorheriger Vorschlag', phrases: ['vorheriger', 'vorherige'], handler: () => speech.selectSuggestionAt(speech.selectedIndex.value - 1) })

async function selectRoutePhrase() {
  const phraseId = Number(route.query.phrase || 0)
  if (!phraseId) return
  try {
    await ready
    const phrase = byId(phraseId)
    if (phrase) speech.selectPhrase(phrase)
  } catch {
    speech.status.value = 'Phrase konnte nicht geladen werden.'
  }
}

function startRecording() {
  if (speech.isRecording.value || speech.isBusy.value) return
  const shouldResumeVoiceCommands = speechCommands.isListening.value
  speechCommands.stop()
  void speech.startRecording().finally(() => {
    if (shouldResumeVoiceCommands) {
      speechCommands.start()
    }
  })
}

function submit() {
  speech.speakSelected()
}
</script>

<template>
  <form
    class="flex flex-1 flex-col justify-start gap-5"
    @submit.prevent="submit"
  >
    <RecordControl
      :is-recording="speech.isRecording.value"
      :is-busy="speech.isBusy.value"
      @start="startRecording"
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

    <SpeechCommandControl
      :is-listening="speechCommands.isListening.value"
      :is-supported="speechCommands.isSupported.value"
      :status="speechCommands.status.value"
      @start="speechCommands.start"
      @stop="speechCommands.stop"
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

    <UButton
      class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="neutral"
      icon="i-lucide-list-checks"
      size="xl"
      to="/labeling"
      variant="subtle"
    >
      Aufnahmen prüfen
    </UButton>
  </form>
</template>
