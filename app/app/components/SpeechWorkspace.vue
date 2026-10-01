<script setup lang="ts">
export type SpeechMode = 'text' | 'math' | 'emoji'

const mode = defineModel<SpeechMode>('mode', { required: true })

const modeOptions: Array<{ label: string, value: SpeechMode }> = [
  { label: 'Text', value: 'text' },
  { label: 'Mathe', value: 'math' },
  { label: 'Emoji', value: 'emoji' }
]
const autoStopOnSilence = useLocalStorage('auto-stop-on-silence', true)
const speech = useSpeechSession(mode, autoStopOnSilence)
const speechCommands = useSpeechCommands()
const recognizedEmojis = ref<Array<{ name: string, value: string }>>([])
const recentEmojis = computed(() =>
  [...speech.emojiHistory.value, ...recognizedEmojis.value]
    .filter((emoji, index, emojis) => emojis.findIndex(item => item.value === emoji.value) === index)
    .slice(0, 8)
)

watch(mode, async (value) => {
  if (value !== 'emoji' || recognizedEmojis.value.length) return
  recognizedEmojis.value = await $fetch<Array<{ name: string, value: string }>>('/api/emojis/recent').catch(() => [])
}, { immediate: true })
useSpeechCommand({ id: 'record', label: 'Aufnehmen', phrases: ['aufnehmen', 'aufnahme', 'start', 'los'], handler: startRecording })
useSpeechCommand({ id: 'stop-recording', label: 'Stopp', phrases: ['stopp', 'stop', 'anhalten', 'fertig'], handler: speech.stopRecording })
useSpeechCommand({ id: 'speak', label: 'Vorlesen', phrases: ['vorlesen', 'sagen', 'sprich', 'sprechen'], handler: speech.speakSelected })
useSpeechCommand({ id: 'copy', label: 'Kopieren', phrases: ['kopieren', 'kopie', 'abschreiben'], handler: speech.copySelected })
useSpeechCommand({ id: 'share-text', label: 'Text teilen', phrases: ['teilen', 'senden', 'schicken', 'whatsapp', 'verschicken'], handler: speech.shareText })
useSpeechCommand({ id: 'share-instagram', label: 'Instagram', phrases: ['instagram', 'insta', 'bild teilen'], handler: speech.shareToInstagram })
useSpeechCommand({ id: 'text-mode', label: 'Textmodus', phrases: ['text', 'sätze', 'satzmodus', 'freitext', 'freier text', 'freitextmodus'], handler: () => setMode('text') })
useSpeechCommand({ id: 'math-mode', label: 'Mathemodus', phrases: ['mathe', 'mathemodus'], handler: () => setMode('math') })
useSpeechCommand({ id: 'emoji-mode', label: 'Emojimodus', phrases: ['emoji', 'emojimodus'], handler: () => setMode('emoji') })

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

    <SilenceStopSetting v-model="autoStopOnSilence" />

    <RecordControl
      :is-recording="speech.isRecording.value"
      :is-busy="speech.isBusy.value"
      :start-label="mode === 'text' && speech.freeText.value ? 'Neue Aufnahme' : undefined"
      :start-guidance="mode === 'text' && speech.freeText.value ? 'Startet einen neuen Text' : undefined"
      @start="startRecording"
      @stop="speech.stopRecording"
    />

    <AudioLevelMeter
      v-if="speech.isRecording.value"
      :level="speech.audioLevel.value"
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
      aria-live="polite"
      class="min-h-7 text-center text-lg font-semibold text-toned"
      role="status"
    >
      {{ speech.status.value }}
    </p>

    <FreeTextResult
      v-if="mode === 'text' && speech.freeText.value"
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

    <EmojiQuickAccess
      v-if="mode === 'emoji'"
      :emojis="recentEmojis"
      @select="speech.selectEmoji"
    />

    <LazyEmojiResult
      v-if="speech.hasEmojiResult.value"
      :emoji-name="speech.emojiName.value"
      :emoji-text="speech.emojiText.value"
      @copy="speech.copySelected"
    />

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
