<script setup lang="ts">
import type { Category } from '~/types/speech'

const props = defineProps<{
  category: Category
  isSaving: boolean
}>()

const emit = defineEmits<{
  save: [name: string]
  delete: []
  cancel: []
}>()

const isEditing = ref(false)
const isDeleteModalOpen = ref(false)
const name = ref(props.category.name)

watch(() => props.category.name, (categoryName) => {
  name.value = categoryName
})

function save() {
  emit('save', name.value)
}

function deleteCategory() {
  emit('delete')
}

function cancel() {
  name.value = props.category.name
  isEditing.value = false
}
</script>

<template>
  <UForm
    v-if="isEditing"
    :state="{ name }"
    class="space-y-3"
    @submit="save"
  >
    <UFormField label="Name der Kategorie">
      <UInput
        v-model="name"
        class="w-full"
        size="xl"
      />
    </UFormField>
    <div class="grid gap-3">
      <UButton
        block
        class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
        color="primary"
        icon="i-lucide-save"
        label="Kategorie speichern"
        size="xl"
        type="submit"
        :loading="isSaving"
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
        @click="cancel"
      />
    </div>
  </UForm>
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
  <CategoryDeletionModal
    v-model:open="isDeleteModalOpen"
    :category="props.category"
    :is-saving="isSaving"
    @delete="deleteCategory"
  />
</template>
