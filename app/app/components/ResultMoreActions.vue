<script setup lang="ts">
const props = defineProps<{ disabled?: boolean, audioId?: string }>()
const emit = defineEmits<{
  active: [active: boolean]
  speak: []
  shareText: []
  shareInstagram: []
}>()
const commands = useSpeechCommands()
const open = ref(false)
const showAudio = ref(false)
const audio = ref<HTMLAudioElement>()
const status = ref('')
let releasePlayback: (() => void) | undefined

function resumePlaybackCommands() {
  releasePlayback?.()
  releasePlayback = undefined
}
function stopPlayback() {
  audio.value?.pause()
  resumePlaybackCommands()
}
watch(
  open,
  (value) => {
    emit('active', value)
    if (!value) {
      stopPlayback()
      showAudio.value = false
    }
  },
  { flush: 'sync' }
)
watch(
  () => [props.audioId, props.disabled],
  () => {
    open.value = false
    stopPlayback()
    status.value = ''
  }
)
function speak() {
  open.value = false
  emit('speak')
}
function shareText() {
  open.value = false
  emit('shareText')
}
function shareInstagram() {
  open.value = false
  emit('shareInstagram')
}
async function play() {
  if (!props.audioId || props.disabled) return
  open.value = true
  showAudio.value = true
  commands.speak('')
  await nextTick()
  try {
    await audio.value?.play()
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return
    stopPlayback()
    status.value = 'Die Aufnahme konnte nicht abgespielt werden.'
  }
}
useSpeechCommand({
  id: 'more-actions',
  label: 'Weitere Aktionen',
  phrases: ['weitere aktionen'],
  enabled: () => !props.disabled && !open.value,
  handler: () => {
    open.value = true
  }
})
useSpeechCommand({
  id: 'play-recording',
  label: 'Aufnahme anhören',
  phrases: ['aufnahme anhören', 'anhören'],
  enabled: () => !props.disabled && Boolean(props.audioId),
  handler: play
})
useSpeechCommand({
  id: 'more-speak',
  label: 'Vorlesen',
  phrases: ['vorlesen', 'sagen', 'sprich', 'sprechen'],
  enabled: () => open.value && !props.disabled,
  handler: speak
})
useSpeechCommand({
  id: 'more-share-text',
  label: 'Text teilen',
  phrases: [
    'teilen',
    'senden',
    'schicken',
    'whatsapp',
    'verschicken',
    'text teilen'
  ],
  enabled: () => open.value && !props.disabled,
  handler: shareText
})
useSpeechCommand({
  id: 'more-share-instagram',
  label: 'Instagram',
  phrases: ['instagram', 'insta', 'bild teilen'],
  enabled: () => open.value && !props.disabled,
  handler: shareInstagram
})
useSpeechCommand({
  id: 'close-more-actions',
  label: 'Schließen',
  phrases: ['schließen', 'aktionen schließen'],
  enabled: () => open.value,
  handler: () => {
    open.value = false
  }
})
onBeforeUnmount(() => {
  stopPlayback()
  emit('active', false)
})
</script>

<template>
  <UButton
    block
    class="min-h-20"
    color="neutral"
    variant="outline"
    icon="i-lucide-ellipsis"
    label="Weitere Aktionen"
    size="xl"
    type="button"
    :disabled="disabled"
    @click="open = true"
  />
  <UModal
    v-model:open="open"
    title="Weitere Aktionen"
    description="Teile deinen Text oder höre ihn an."
    :close="false"
    :dismissible="false"
    :transition="false"
    :ui="{ content: 'rounded-3xl', title: 'text-2xl', description: 'text-lg' }"
  >
    <template #body>
      <div class="space-y-4">
        <UButton
          block
          class="min-h-20"
          size="xl"
          type="button"
          color="neutral"
          variant="soft"
          icon="i-lucide-share-2"
          :disabled="disabled"
          @click="shareText"
        >
          Text teilen
        </UButton>
        <UButton
          block
          class="min-h-20"
          size="xl"
          type="button"
          color="neutral"
          variant="soft"
          icon="i-lucide-instagram"
          :disabled="disabled"
          @click="shareInstagram"
        >
          Instagram
        </UButton>
        <UButton
          block
          class="min-h-20"
          icon="i-lucide-volume-2"
          label="Vorlesen"
          size="xl"
          type="button"
          :disabled="disabled"
          @click="speak"
        />
        <UButton
          block
          class="min-h-20"
          size="xl"
          type="button"
          color="neutral"
          variant="soft"
          icon="i-lucide-headphones"
          :disabled="disabled || !audioId"
          @click="play"
        >
          Aufnahme anhören
        </UButton>
        <audio
          v-if="showAudio && audioId"
          ref="audio"
          class="w-full"
          controls
          preload="none"
          :src="`/api/labeling/audio/${audioId}`"
          @play="
            commands.speak('');
            releasePlayback ||= commands.pause();
          "
          @pause="resumePlaybackCommands"
          @ended="resumePlaybackCommands"
          @error="resumePlaybackCommands"
        />
        <p
          v-if="status"
          role="status"
          aria-live="polite"
          class="text-lg text-toned"
        >
          {{ status }}
        </p>
      </div>
    </template>
    <template #footer>
      <UButton
        block
        class="min-h-20"
        size="xl"
        type="button"
        color="neutral"
        variant="outline"
        @click="open = false"
      >
        Schließen
      </UButton>
    </template>
  </UModal>
</template>
