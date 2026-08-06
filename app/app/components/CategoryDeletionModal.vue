<script lang="ts" setup>
import type { Category } from '~/types/speech'

defineProps<{
  category: Category
  isSaving: boolean
}>()

const emit = defineEmits<{
  delete: []
}>()

const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <UModal
    v-model:open="open"
    title="Kategorie löschen?"
    :description="`${category.phrase_count} Sätze werden auch gelöscht.`"
    :close="false"
  >
    <template #body>
      <p class="text-xl font-bold leading-snug text-highlighted">
        {{ category.name }}
      </p>
    </template>

    <template #footer>
      <div class="grid w-full gap-3">
        <UButton
          block
          class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
          color="error"
          icon="i-lucide-trash-2"
          label="Kategorie und Sätze löschen"
          size="xl"
          type="button"
          :loading="isSaving"
          @click="emit('delete')"
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
          :disabled="isSaving"
          @click="open = false"
        />
      </div>
    </template>
  </UModal>
</template>
