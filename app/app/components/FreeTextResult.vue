<script setup lang="ts">
defineProps<{
  disabled?: boolean
  text: string
  audioId?: string
}>()

defineEmits<{
  copy: []
  shareInstagram: []
  shareText: []
  updateText: [text: string]
  reviewActive: [active: boolean]
  reviewBusy: [busy: boolean]
}>()
const correctionBusy = ref(false)
</script>

<template>
  <section class="space-y-4">
    <TranscriptReview
      :text="text"
      :audio-id="audioId"
      :disabled="disabled"
      @update-text="$emit('updateText', $event)"
      @active="$emit('reviewActive', $event)"
      @busy="correctionBusy = $event; $emit('reviewBusy', $event)"
    />

    <UButton
      block
      class="min-h-20"
      color="primary"
      icon="i-lucide-copy"
      label="Kopieren"
      size="xl"
      type="button"
      :disabled="disabled || correctionBusy || !text"
      @click="$emit('copy')"
    />

    <ResultActions
      :disabled="disabled || correctionBusy || !text"
      @share-instagram="$emit('shareInstagram')"
      @share-text="$emit('shareText')"
    />
  </section>
</template>
