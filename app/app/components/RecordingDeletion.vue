<script setup lang="ts">
import type { LabelItem } from '~/types/speech'

const props = defineProps<{
  recording: LabelItem
  disabled?: boolean
}>()

const emit = defineEmits<{
  deleted: []
}>()

const isDeleting = ref(false)
const isModalOpen = ref(false)

function closeModal(isOpen: boolean) {
  if (!isOpen && !isDeleting.value) isModalOpen.value = false
}

async function deleteRecording() {
  if (isDeleting.value) return
  isDeleting.value = true
  try {
    await $fetch(`/api/labeling/items/${props.recording.audio_id}`, {
      method: 'DELETE'
    })
    isModalOpen.value = false
    emit('deleted')
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <UButton
    block
    class="min-h-12 justify-center font-extrabold"
    color="error"
    icon="i-lucide-trash-2"
    size="lg"
    variant="ghost"
    :disabled="disabled || isDeleting"
    @click="isModalOpen = true"
  >
    Aufnahme löschen
  </UButton>

  <UModal
    :open="isModalOpen"
    title="Aufnahme löschen?"
    description="Die Audio-Datei und ihr Label werden dauerhaft entfernt."
    :close="false"
    @update:open="closeModal"
  >
    <template #body>
      <p class="text-xl font-bold leading-snug text-highlighted">
        {{ recording.original_filename || recording.audio_file }}
      </p>
    </template>

    <template #footer>
      <div class="grid w-full gap-3">
        <UButton
          block
          class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
          color="error"
          icon="i-lucide-trash-2"
          label="Ja, dauerhaft löschen"
          size="xl"
          type="button"
          :loading="isDeleting"
          @click="deleteRecording"
        />
        <UButton
          block
          class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
          color="neutral"
          icon="i-lucide-x"
          label="Abbrechen"
          size="xl"
          type="button"
          variant="subtle"
          :disabled="isDeleting"
          @click="isModalOpen = false"
        />
      </div>
    </template>
  </UModal>
</template>
