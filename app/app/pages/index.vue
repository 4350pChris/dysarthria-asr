<script setup lang="ts">
const route = useRoute()

definePageMeta({
  pageHeader: {
    eyebrow: 'Sprachhilfe',
    title: 'Was möchtest du sagen?'
  }
})

type Mode = 'phrases' | 'math' | 'emoji' | 'freetext'

const mode = ref<Mode>('freetext')
const modeOptions: Array<{ label: string, value: Mode }> = [
  { label: 'Sätze', value: 'phrases' },
  { label: 'Mathe', value: 'math' },
  { label: 'Emoji', value: 'emoji' },
  { label: 'Freitext', value: 'freetext' }
]
const speech = useSpeechSession(mode)
const { byId, ready } = usePhrases()
const speechCommands = useSpeechCommands()

await selectRoutePhrase()
useSpeechCommand({ id: 'record', label: 'Aufnehmen', phrases: ['aufnehmen', 'aufnahme', 'start', 'los'], handler: startRecording })
useSpeechCommand({ id: 'stop-recording', label: 'Stopp', phrases: ['stopp', 'stop', 'anhalten', 'fertig'], handler: speech.stopRecording })
useSpeechCommand({ id: 'speak', label: 'Vorlesen', phrases: ['vorlesen', 'sagen', 'sprich', 'sprechen'], handler: submit })
useSpeechCommand({ id: 'copy', label: 'Kopieren', phrases: ['kopieren', 'kopie', 'abschreiben'], handler: speech.copySelected })
useSpeechCommand({ id: 'share-text', label: 'Text teilen', phrases: ['teilen', 'senden', 'schicken', 'whatsapp', 'verschicken'], handler: speech.shareText })
useSpeechCommand({ id: 'share-instagram', label: 'Instagram', phrases: ['instagram', 'insta', 'bild teilen'], handler: speech.shareToInstagram })
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
useSpeechCommand({
  id: 'freetext-mode',
  label: 'Freitextmodus',
  phrases: ['freitext', 'freier text', 'freitextmodus'],
  handler: () => {
    mode.value = 'freetext'
    speech.status.value = 'Freitextmodus.'
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
      :start-label="mode === 'freetext' && speech.freeText.value ? 'Neue Aufnahme' : undefined"
      :start-guidance="mode === 'freetext' && speech.freeText.value ? 'Startet einen neuen Text' : undefined"
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
          class="min-h-16 justify-center rounded-2xl px-3 text-center text-lg font-extrabold"
          :color="mode === option.value ? 'primary' : 'neutral'"
          size="xl"
          type="button"
          :variant="mode === option.value ? 'solid' : 'outline'"
          :class="{ 'col-span-3': option.value === 'freetext' }"
          @click="mode = option.value"
        >
          {{ option.label }}
        </UButton>
      </div>
    </fieldset>

    <p
      aria-live="polite"
      class="min-h-7 text-center text-lg font-semibold text-toned"
      role="status"
    >
      {{ speech.status.value }}
    </p>

    <section
      v-if="mode === 'freetext' && speech.isRecording.value && speech.freeText.value"
      aria-label="Erkannter Freitext"
      class="rounded-2xl border border-default bg-elevated p-5 text-xl font-semibold leading-relaxed"
    >
      {{ speech.freeText.value }}
    </section>

    <section
      v-if="speech.hasSelection.value && mode === 'phrases'"
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

    <LazyMathResult
      v-if="speech.hasMathResult.value && speech.result.value"
      :math-text="speech.result.value.math_text"
      :corrected-text="speech.result.value.math_corrected_text"
      @copy="speech.copySelected"
      @share-instagram="speech.shareToInstagram"
      @share-text="speech.shareText"
    />

    <LazyEmojiResult
      v-if="speech.hasEmojiResult.value && speech.result.value"
      :emoji-name="speech.result.value.emoji_name"
      :emoji-text="speech.result.value.emoji_value"
      @copy="speech.copySelected"
    />

    <LazyFreeTextResult
      v-if="mode === 'freetext' && !speech.isRecording.value && !speech.isBusy.value && speech.freeText.value"
      :text="speech.freeText.value"
      @copy="speech.copySelected"
      @share-instagram="speech.shareToInstagram"
      @share-text="speech.shareText"
      @update-text="speech.setFreeText"
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
      color="primary"
      icon="i-lucide-book-open-check"
      size="xl"
      to="/training"
      variant="soft"
    >
      Lesetraining aufnehmen
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
