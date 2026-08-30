<script setup lang="ts">
defineProps<{
  isBusy: boolean
  isRecording: boolean
}>()

const emit = defineEmits<{
  start: []
  stop: []
}>()
</script>

<template>
  <RecordControl
    :is-busy="isBusy"
    :is-recording="isRecording"
    @start="emit('start')"
    @stop="emit('stop')"
  >
    <template #default="{ isBusy: busy, isRecording: recording, toggle }">
      <UButton
        block
        class="min-h-28 rounded-3xl text-xl"
        :color="recording ? 'error' : 'primary'"
        :disabled="busy"
        :icon="recording ? 'i-lucide-square' : 'i-lucide-mic'"
        size="xl"
        @click="toggle"
      >
        {{ recording ? 'Aufnahme stoppen' : 'Diesen Text aufnehmen' }}
      </UButton>
    </template>
  </RecordControl>
</template>
