<script setup lang="ts">
defineProps<{
  emojiText: string
  emojiName: string
}>()

defineEmits<{
  copy: []
}>()
</script>

<template>
  <section class="space-y-4">
    <UCard>
      <p class="text-sm font-semibold text-muted">
        Emoji erkannt
      </p>
      <p
        class="mt-2 text-7xl leading-tight"
        role="img"
        :aria-label="emojiName"
      >
        {{ emojiText }}
      </p>
      <p class="mt-3 text-lg font-semibold text-muted">
        {{ emojiName }}
      </p>
    </UCard>

    <UButton
      block
      class="min-h-20"
      color="primary"
      icon="i-lucide-copy"
      label="Emoji kopieren"
      size="xl"
      type="button"
      @click="$emit('copy')"
    />
  </section>
</template>
