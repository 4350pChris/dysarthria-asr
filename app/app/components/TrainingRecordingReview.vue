<script setup lang="ts">
import type { AudioQualityReport } from '~/utils/audioQuality'

const props = defineProps<{
  audioQuality?: AudioQualityReport
  canSave: boolean
  isCheckingAudio: boolean
  isSaving: boolean
  recordingUrl: string
}>()

const emit = defineEmits<{
  retry: []
}>()
</script>

<template>
  <audio
    class="w-full"
    controls
    :src="recordingUrl"
  />
  <UAlert
    v-if="isCheckingAudio"
    color="info"
    icon="i-lucide-audio-lines"
    title="Aufnahme wird geprüft"
    description="Bitte warte kurz."
  />
  <UAlert
    v-else-if="props.audioQuality?.issues.length"
    :color="canSave ? 'warning' : 'error'"
    icon="i-lucide-circle-alert"
    title="Aufnahme prüfen"
    :description="props.audioQuality.issues.map(issue => issue.message).join(' ')"
  />
  <div class="grid grid-cols-2 gap-3">
    <UButton
      block
      color="neutral"
      icon="i-lucide-rotate-ccw"
      size="xl"
      variant="soft"
      :disabled="isSaving"
      type="button"
      @click="emit('retry')"
    >
      Neu aufnehmen
    </UButton>
    <UButton
      block
      color="primary"
      icon="i-lucide-save"
      size="xl"
      :disabled="!canSave"
      :loading="isSaving || isCheckingAudio"
      type="submit"
    >
      Als Trainingspaar speichern
    </UButton>
  </div>
</template>
