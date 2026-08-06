<script setup lang="ts">
import type { Category } from '~/types/speech'

const props = defineProps<{
  category: Category
}>()

const { refreshAfterCategoryChange } = usePhrases()
const status = ref('')
const isSaving = ref(false)

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
  } catch (error) {
    status.value = apiErrorMessage(error, 'Kategorie konnte nicht geändert werden.')
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
  } catch (error) {
    status.value = apiErrorMessage(error, 'Kategorie konnte nicht gelöscht werden.')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="space-y-3">
    <CategoryEditForm
      :category="category"
      :is-saving="isSaving"
      @delete="deleteCategory"
      @save="saveCategory"
    />
    <p
      v-if="status"
      class="text-lg font-semibold text-toned"
      role="status"
    >
      {{ status }}
    </p>
  </section>
</template>
