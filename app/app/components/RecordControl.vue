<script setup lang="ts">
defineProps<{
  isRecording: boolean
  isBusy: boolean
}>()

defineEmits<{
  start: []
  stop: []
}>()
</script>

<template>
  <UButton
    v-if="!isRecording"
    class="min-h-60 rounded-3xl text-3xl font-extrabold shadow-lg"
    block
    color="primary"
    icon="i-lucide-mic"
    size="xl"
    type="button"
    :disabled="isBusy"
    :ui="{ leadingIcon: 'size-12', base: 'flex-col gap-4' }"
    @click="$emit('start')"
  >
    Aufnehmen
  </UButton>

  <UButton
    v-else
    class="min-h-60 justify-center rounded-3xl text-3xl font-extrabold shadow-lg"
    block
    color="error"
    icon="i-lucide-square"
    size="xl"
    type="button"
    :ui="{ leadingIcon: 'size-12', base: 'flex-col gap-4' }"
    @click="$emit('stop')"
  >
    Stopp
  </UButton>
</template>
