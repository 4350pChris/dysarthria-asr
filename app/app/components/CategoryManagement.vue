<script setup lang="ts">
import type { Category } from '~/types/speech'

const props = defineProps<{
  category: Category
}>()

const { refreshAfterCategoryChange } = usePhrases()
const status = ref('')
const isDeleting = ref(false)

async function categorySaved(name: string) {
  await refreshAfterCategoryChange()
  await navigateTo(`/phrases/${encodeURIComponent(name)}`, { replace: true })
}

async function deleteCategory() {
  if (isDeleting.value) return
  isDeleting.value = true
  try {
    await $fetch(`/api/categories/${props.category.id}`, { method: 'DELETE' })
    await refreshAfterCategoryChange()
    await navigateTo('/phrases')
  } catch (error) {
    status.value = apiErrorMessage(error, 'Kategorie konnte nicht gelöscht werden.')
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <section class="space-y-3">
    <CategoryEditForm
      :category="category"
      :is-deleting="isDeleting"
      @delete="deleteCategory"
      @saved="categorySaved"
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
