<script setup lang="ts">
export type SpeechMode = 'text' | 'math' | 'emoji'

const route = useRoute()
const mode = defineModel<SpeechMode>('mode', { required: true })

const modeOptions: Array<{ label: string, value: SpeechMode }> = [
  { label: 'Text', value: 'text' },
  { label: 'Mathe', value: 'math' },
  { label: 'Emoji', value: 'emoji' }
]
const speech = useSpeechSession(mode)
const { byId, ready } = usePhrases()
const speechCommands = useSpeechCommands()

await selectRoutePhrase()
useSpeechCommand({ id: 'record', label: 'Aufnehmen', phrases: ['aufnehmen', 'aufnahme', 'start', 'los'], handler: startRecording })
useSpeechCommand({ id: 'stop-recording', label: 'Stopp', phrases: ['stopp', 'stop', 'anhalten', 'fertig'], handler: speech.stopRecording })
useSpeechCommand({ id: 'speak', label: 'Vorlesen', phrases: ['vorlesen', 'sagen', 'sprich', 'sprechen'], handler: speech.speakSelected })
useSpeechCommand({ id: 'copy', label: 'Kopieren', phrases: ['kopieren', 'kopie', 'abschreiben'], handler: speech.copySelected })
useSpeechCommand({ id: 'share-text', label: 'Text teilen', phrases: ['teilen', 'senden', 'schicken', 'whatsapp', 'verschicken'], handler: speech.shareText })
useSpeechCommand({ id: 'share-instagram', label: 'Instagram', phrases: ['instagram', 'insta', 'bild teilen'], handler: speech.shareToInstagram })
useSpeechCommand({ id: 'text-mode', label: 'Textmodus', phrases: ['text', 'sätze', 'satzmodus', 'freitext', 'freier text', 'freitextmodus'], handler: () => setMode('text') })
useSpeechCommand({ id: 'math-mode', label: 'Mathemodus', phrases: ['mathe', 'mathemodus'], handler: () => setMode('math') })
useSpeechCommand({ id: 'emoji-mode', label: 'Emojimodus', phrases: ['emoji', 'emojimodus'], handler: () => setMode('emoji') })
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

function setMode(nextMode: SpeechMode) {
  mode.value = nextMode
  speech.status.value = `${modeOptions.find(option => option.value === nextMode)?.label}modus.`
}

function startRecording() {
  if (speech.isRecording.value || speech.isBusy.value) return
  const shouldResumeVoiceCommands = speechCommands.isListening.value
  speechCommands.stop()
  void speech.startRecording().finally(() => {
    if (shouldResumeVoiceCommands) speechCommands.start()
  })
}
</script>

<template>
  <form
    class="flex flex-1 flex-col justify-start gap-5"
    @submit.prevent="speech.speakSelected"
  >
    <ClientOnly>
      <SpeechCommandControl
        :is-listening="speechCommands.isListening.value"
        :is-supported="speechCommands.isSupported.value"
        :status="speechCommands.status.value"
        @start="speechCommands.start"
        @stop="speechCommands.stop"
      />
    </ClientOnly>

    <RecordControl
      :is-recording="speech.isRecording.value"
      :is-busy="speech.isBusy.value"
      :start-label="mode === 'text' && speech.freeText.value ? 'Neue Aufnahme' : undefined"
      :start-guidance="mode === 'text' && speech.freeText.value ? 'Startet einen neuen Text' : undefined"
      @start="startRecording"
      @stop="speech.stopRecording"
    />

    <fieldset>
      <legend class="sr-only">
        Modus
      </legend>
      <div class="grid w-full grid-cols-3 gap-3">
        <UButton
          v-for="option in modeOptions"
          :key="option.value"
          :aria-pressed="mode === option.value"
          block
          :color="mode === option.value ? 'primary' : 'neutral'"
          size="xl"
          type="button"
          :variant="mode === option.value ? 'solid' : 'outline'"
          @click="setMode(option.value)"
        >
          {{ option.label }}
        </UButton>
      </div>
    </fieldset>

    <p
      v-if="speech.isRecording.value"
      aria-live="polite"
      class="min-h-7 text-center text-lg font-semibold text-toned"
      role="status"
    >
      {{ speech.status.value }}
    </p>

    <section
      v-if="speech.hasSelection.value && mode === 'text' && !speech.showsFreeText.value"
      class="space-y-4"
    >
      <LazyMatchedPhrase
        :raw-transcript="speech.result.value?.raw_transcript"
        :selected="speech.selected.value"
        @copy="speech.copySelected"
        @share-instagram="speech.shareToInstagram"
        @share-text="speech.shareText"
      />
      <LazySuggestionList
        :suggestions="speech.suggestions.value"
        :selected="speech.selected.value"
        @select="speech.setSelection"
      />
    </section>

    <LazyFreeTextResult
      v-if="speech.showsFreeText.value && speech.freeText.value"
      :disabled="speech.isRecording.value || speech.isBusy.value"
      :text="speech.freeText.value"
      @copy="speech.copySelected"
      @share-instagram="speech.shareToInstagram"
      @share-text="speech.shareText"
      @update-text="speech.setFreeText"
    />

    <MathWorkspace
      v-if="mode === 'math'"
      :speech="speech"
    />

    <LazyEmojiResult
      v-if="speech.hasEmojiResult.value && speech.result.value"
      :emoji-name="speech.result.value.emoji_name"
      :emoji-text="speech.result.value.emoji_value"
      @copy="speech.copySelected"
    />

    <UButton
      class="min-h-24 text-xl"
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
      block
      color="primary"
      icon="i-lucide-book-open-check"
      size="xl"
      to="/training"
      variant="soft"
    >
      Lesetraining aufnehmen
    </UButton>

    <UButton
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
