<script setup lang="ts">
defineProps<{
  disabled?: boolean
  text: string
}>()

defineEmits<{
  copy: []
  shareInstagram: []
  shareText: []
  updateText: [text: string]
}>()
</script>

<template>
  <section class="space-y-4">
    <UTextarea
      :model-value="text"
      aria-label="Erkannter Freitext"
      autoresize
      class="w-full"
      :readonly="disabled"
      :rows="7"
      size="xl"
      :ui="{ base: 'min-h-56 rounded-2xl p-5 text-xl font-semibold leading-relaxed' }"
      @update:model-value="$emit('updateText', $event)"
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
