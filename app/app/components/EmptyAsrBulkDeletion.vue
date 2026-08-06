<script setup lang="ts">
import type { AudioSource, LabelStatus } from '~/types/speech'

const props = defineProps<{
  count: number
  source: AudioSource | 'all'
  status: LabelStatus | 'all'
  unsureOnly: boolean
}>()

const emit = defineEmits<{ deleted: [] }>()

const isDeleting = ref(false)
const isModalOpen = ref(false)

const query = computed(() => ({
  ...(props.source !== 'all' ? { source: props.source } : {}),
  ...(props.status !== 'all' ? { status: props.status } : {}),
  ...(props.unsureOnly ? { unsure: true } : {})
}))

function closeModal(isOpen: boolean) {
  if (!isOpen && !isDeleting.value) isModalOpen.value = false
}

async function deleteItems() {
  if (isDeleting.value) return
  isDeleting.value = true
  try {
    await $fetch('/api/labeling/items/empty-asr', {
      method: 'DELETE',
      query: query.value
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
    v-if="count"
    block
    class="min-h-12 justify-center font-extrabold"
    color="error"
    icon="i-lucide-trash-2"
    size="lg"
    variant="soft"
    @click="isModalOpen = true"
  >
    {{ count }} Audios ohne ASR-Text löschen
  </UButton>

  <UModal
    :open="isModalOpen"
    title="Audios ohne ASR-Text löschen?"
    :description="`${count} Audio-Dateien und ihre Labels werden dauerhaft entfernt.`"
    :close="false"
    @update:open="closeModal"
  >
    <template #body>
      <p class="text-base text-muted">
        Die aktuellen Filter für Quelle, Status und Unsicherheit gelten auch hier.
      </p>
    </template>

    <template #footer>
      <div class="grid w-full gap-3">
        <UButton
          block
          color="error"
          icon="i-lucide-trash-2"
          size="xl"
          :loading="isDeleting"
          @click="deleteItems"
        >
          {{ count }} Audios dauerhaft löschen
        </UButton>
        <UButton
          block
          color="neutral"
          size="xl"
          variant="subtle"
          :disabled="isDeleting"
          @click="isModalOpen = false"
        >
          Abbrechen
        </UButton>
      </div>
    </template>
  </UModal>
</template>
