<script setup lang="ts">
export type SpeechMode = 'text' | 'math' | 'emoji'

const mode = defineModel<SpeechMode>('mode', { required: true })

const modeOptions: Array<{ label: string, value: SpeechMode }> = [
  { label: 'Text', value: 'text' },
  { label: 'Mathe', value: 'math' },
  { label: 'Emoji', value: 'emoji' }
]
const autoStopOnSilence = useLocalStorage('auto-stop-on-silence', true)
const reviewActive = ref(false)
const resultPanel = ref<HTMLElement>()
const speech = useSpeechSession(mode, autoStopOnSilence)
const speechCommands = useSpeechCommands()
const recognizedEmojis = ref<Array<{ name: string, value: string }>>([])
const recentEmojis = computed(() =>
  [...speech.emojiHistory.value, ...recognizedEmojis.value]
    .filter((emoji, index, emojis) => emojis.findIndex(item => item.value === emoji.value) === index)
    .slice(0, 8)
)

watch(speech.isBusy, async (busy, wasBusy) => {
  if (busy || !wasBusy || mode.value !== 'text' || !speech.result.value || !speech.freeText.value) return
  await nextTick()
  resultPanel.value?.scrollIntoView({ block: 'start', behavior: 'instant' })
})

watch(mode, async (value) => {
  if (value !== 'emoji' || recognizedEmojis.value.length) return
  recognizedEmojis.value = await $fetch<Array<{ name: string, value: string }>>('/api/emojis/recent').catch(() => [])
}, { immediate: true })
useSpeechCommand({ id: 'record', label: 'Aufnehmen', phrases: ['aufnehmen', 'aufnahme', 'start', 'los'], enabled: () => !reviewActive.value, handler: startRecording })
useSpeechCommand({ id: 'stop-recording', label: 'Stopp', phrases: ['stopp', 'stop', 'anhalten', 'fertig'], enabled: () => !reviewActive.value, handler: speech.stopRecording })
useSpeechCommand({ id: 'speak', label: 'Vorlesen', phrases: ['vorlesen', 'sagen', 'sprich', 'sprechen'], enabled: () => !reviewActive.value, handler: speech.speakSelected })
useSpeechCommand({ id: 'copy', label: 'Kopieren', phrases: ['kopieren', 'kopie', 'abschreiben'], enabled: () => !reviewActive.value, handler: speech.copySelected })
useSpeechCommand({ id: 'share-text', label: 'Text teilen', phrases: ['teilen', 'senden', 'schicken', 'whatsapp', 'verschicken', 'text teilen'], enabled: () => !reviewActive.value, handler: speech.shareText })
useSpeechCommand({ id: 'share-instagram', label: 'Instagram', phrases: ['instagram', 'insta', 'bild teilen'], enabled: () => !reviewActive.value, handler: speech.shareToInstagram })
useSpeechCommand({ id: 'text-mode', label: 'Textmodus', phrases: ['text', 'sätze', 'satzmodus', 'freitext', 'freier text', 'freitextmodus'], enabled: () => !reviewActive.value, handler: () => setMode('text') })
useSpeechCommand({ id: 'math-mode', label: 'Mathemodus', phrases: ['mathe', 'mathemodus'], enabled: () => !reviewActive.value, handler: () => setMode('math') })
useSpeechCommand({ id: 'emoji-mode', label: 'Emojimodus', phrases: ['emoji', 'emojimodus'], enabled: () => !reviewActive.value, handler: () => setMode('emoji') })

function setMode(nextMode: SpeechMode) {
  if (reviewActive.value || speech.isBusy.value || speech.isRecording.value) return
  mode.value = nextMode
  speech.status.value = `${modeOptions.find(option => option.value === nextMode)?.label}modus.`
}

function startRecording() {
  if (speech.isRecording.value || speech.isBusy.value || reviewActive.value) return
  speechCommands.speak('')
  const resume = speechCommands.pause()
  void speech.startRecording().catch(() => {
    speech.status.value = 'Aufnahme nicht möglich.'
  }).finally(() => {
    resume()
  })
}
</script>

<template>
  <form
    class="flex flex-1 flex-col justify-start gap-5"
    @submit.prevent="speech.speakSelected"
  >
    <RecordControl
      :is-recording="speech.isRecording.value"
      :is-busy="speech.isBusy.value || reviewActive"
      :start-label="mode === 'text' && speech.freeText.value ? 'Neue Aufnahme' : undefined"
      :start-guidance="mode === 'text' && speech.freeText.value ? 'Startet einen neuen Text' : undefined"
      @start="startRecording"
      @stop="speech.stopRecording"
    />

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
          :disabled="reviewActive || speech.isBusy.value || speech.isRecording.value"
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

    <div
      v-if="mode === 'text' && speech.freeText.value"
      ref="resultPanel"
      class="scroll-mt-20"
    >
      <FreeTextResult
        :disabled="speech.isRecording.value || speech.isBusy.value"
        :text="speech.freeText.value"
        :audio-id="speech.result.value?.audio_id"
        @speak="speech.speakSelected"
        @copy="speech.copySelected"
        @share-instagram="speech.shareToInstagram"
        @share-text="speech.shareText"
        @update-text="speech.setFreeText"
        @review-active="reviewActive = $event"
      />
    </div>

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
  </form>
</template>
