<script setup lang="ts">
const props = defineProps<{
  disabled?: boolean
  text: string
  audioId?: string
}>()

const emit = defineEmits<{
  speak: []
  copy: []
  shareInstagram: []
  shareText: []
  updateText: [text: string]
  reviewActive: [active: boolean]
}>()
const reviewActive = ref(false)
const moreActive = ref(false)
watch([reviewActive, moreActive], ([reviewing, more]) => emit('reviewActive', reviewing || more), { flush: 'sync' })
</script>

<template>
  <section class="space-y-4">
    <TranscriptReview
      :text="text"
      :audio-id="audioId"
      :disabled="disabled"
      :inactive="moreActive"
      @update-text="$emit('updateText', $event)"
      @active="reviewActive = $event"
    />

    <UButton
      block
      class="min-h-20"
      color="neutral"
      variant="soft"
      icon="i-lucide-copy"
      label="Kopieren"
      size="xl"
      type="button"
      :disabled="disabled || !text"
      @click="emit('copy')"
    />
    <ResultMoreActions
      :disabled="props.disabled || reviewActive"
      :audio-id="audioId"
      @active="moreActive = $event"
      @speak="emit('speak')"
      @share-instagram="emit('shareInstagram')"
      @share-text="emit('shareText')"
    />
  </section>
</template>
