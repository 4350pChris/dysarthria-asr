<script setup lang="ts">
import type { Category } from '~/types/speech'

const props = defineProps<{
  category: Category
}>()

const { refreshAfterCategoryChange } = usePhrases()
const status = ref('')
const isEditing = ref(false)
const isSaving = ref(false)
const isDeleteModalOpen = ref(false)

function cancelEdit() {
  isEditing.value = false
}

async function saveCategory(name: string) {
  const cleanName = name.trim()
  if (!cleanName || isSaving.value) return
  isSaving.value = true
  try {
    const form = new FormData()
    form.append('name', cleanName)
    await $fetch(`/api/categories/${props.category.id}`, { method: 'PATCH', body: form })
    await refreshAfterCategoryChange()
    await navigateTo(`/phrases/${encodeURIComponent(cleanName)}`, { replace: true })
  } catch {
    status.value = 'Kategorie konnte nicht geändert werden.'
  } finally {
    isSaving.value = false
  }
}

async function deleteCategory() {
  if (isSaving.value) return
  isSaving.value = true
  try {
    await $fetch(`/api/categories/${props.category.id}`, { method: 'DELETE' })
    await refreshAfterCategoryChange()
    await navigateTo('/phrases')
  } catch {
    status.value = 'Kategorie konnte nicht gelöscht werden.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="space-y-3">
    <p
      v-if="status"
      class="text-lg font-semibold text-toned"
    >
      {{ status }}
    </p>

    <CategoryEditForm
      v-if="isEditing"
      :category="category"
      :is-saving="isSaving"
      @cancel="cancelEdit"
      @save="saveCategory"
    />

    <div
      v-else
      class="grid gap-3"
    >
      <UButton
        block
        class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
        color="neutral"
        icon="i-lucide-pencil"
        label="Kategorie ändern"
        size="xl"
        type="button"
        variant="subtle"
        @click="isEditing = true"
      />
      <UButton
        block
        class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
        color="error"
        icon="i-lucide-trash-2"
        label="Kategorie löschen"
        size="xl"
        type="button"
        variant="subtle"
        @click="isDeleteModalOpen = true"
      />
    </div>

    <UModal
      :open="isDeleteModalOpen"
      title="Kategorie löschen?"
      :description="`${category.phrase_count} Sätze werden auch gelöscht.`"
      :close="false"
      @update:open="isDeleteModalOpen = $event"
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
            @click="deleteCategory"
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
            @click="isDeleteModalOpen = false"
          />
        </div>
      </template>
    </UModal>
  </section>
</template>
