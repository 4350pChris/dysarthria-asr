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
}>()
</script>

<template>
  <section class="space-y-4">
    <TranscriptReview
      :text="text"
      :audio-id="audioId"
      :disabled="disabled"
      @update-text="$emit('updateText', $event)"
      @active="$emit('reviewActive', $event)"
    />

    <UButton
      block
      class="min-h-20"
      color="primary"
      icon="i-lucide-copy"
      label="Kopieren"
      size="xl"
      type="button"
      :disabled="disabled || !text"
      @click="$emit('copy')"
    />

    <ResultActions
      :disabled="disabled || !text"
      @share-instagram="$emit('shareInstagram')"
      @share-text="$emit('shareText')"
    />
  </section>
</template>
