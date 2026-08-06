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
  <section class="space-y-3">
    <UButton
      v-if="!isListening"
      block
      class="min-h-20 justify-center rounded-2xl text-lg font-extrabold"
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
      class="min-h-20 justify-center rounded-2xl text-lg font-extrabold"
      color="warning"
      icon="i-lucide-audio-lines"
      label="Sprachsteuerung stoppen"
      size="xl"
      type="button"
      variant="subtle"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-2' }"
      @click="$emit('stop')"
    />
    <p class="min-h-6 text-center text-sm font-semibold text-muted">
      {{ isSupported ? status : 'Sprachsteuerung braucht Chrome oder einen kompatiblen Browser.' }}
    </p>
  </section>
</template>
