<script setup lang="ts">
defineProps<{
  isSupported: boolean
  isListening: boolean
  status: string
}>()

defineEmits<{
  start: []
  stop: []
}>()
</script>

<template>
  <section
    v-if="isSupported"
    class="space-y-3"
  >
    <UButton
      v-if="!isListening"
      block
      class="min-h-20"
      color="neutral"
      icon="i-lucide-audio-lines"
      label="Sprachsteuerung starten"
      size="xl"
      type="button"
      variant="subtle"
      :disabled="!isSupported"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-2' }"
      @click="$emit('start')"
    />
    <UButton
      v-else
      block
      class="min-h-20"
      color="warning"
      icon="i-lucide-audio-lines"
      label="Sprachsteuerung stoppen"
      size="xl"
      type="button"
      variant="subtle"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-2' }"
      @click="$emit('stop')"
    />
  </section>
</template>
