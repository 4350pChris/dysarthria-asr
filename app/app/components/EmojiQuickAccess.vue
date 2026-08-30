<script setup lang="ts">
defineProps<{
  emojis: Array<{ name: string, value: string }>
}>()

defineEmits<{
  select: [emoji: { name: string, value: string }]
}>()
</script>

<template>
  <section class="space-y-3">
    <p
      v-if="!emojis.length"
      class="text-center text-lg font-semibold text-muted"
    >
      Sprich ein Emoji ein. Hier stehen danach deine zuletzt verwendeten Emojis.
    </p>
    <div
      v-else
      class="grid grid-cols-4 gap-3"
    >
      <UButton
        v-for="emoji in emojis"
        :key="emoji.value"
        :aria-label="emoji.name"
        class="min-h-20 justify-center text-4xl"
        color="neutral"
        size="xl"
        type="button"
        variant="soft"
        @click="$emit('select', emoji)"
      >
        {{ emoji.value }}
      </UButton>
    </div>
  </section>
</template>
