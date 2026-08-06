<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Category } from '~/types/speech'

type CategoryFormState = { name: string }

const props = defineProps<{
  category: Category
  isDeleting: boolean
}>()

const emit = defineEmits<{
  saved: [name: string]
  delete: []
}>()

const isEditing = ref(false)
const isDeleteModalOpen = ref(false)
const name = ref(props.category.name)
const { clearErrors, formErrors, isSaving, submit } = useFormSubmission<CategoryFormState>('Kategorie konnte nicht geändert werden.')
const isBusy = computed(() => isSaving.value || props.isDeleting)

watch(() => props.category.name, (categoryName) => {
  name.value = categoryName
})
watch(name, clearErrors)

async function save(event: FormSubmitEvent<CategoryFormState>) {
  const saved = await submit(event, data => $fetch<Category>(`/api/categories/${props.category.id}`, {
    method: 'PATCH',
    body: data
  }))
  if (!saved) return
  isEditing.value = false
  emit('saved', saved.name)
}

function deleteCategory() {
  emit('delete')
}

function cancel() {
  name.value = props.category.name
  isEditing.value = false
  clearErrors()
}
</script>

<template>
  <UForm
    v-if="isEditing"
    :state="{ name }"
    class="space-y-3"
    @submit="save"
  >
    <UFormField
      :error="formErrors.name || formErrors._form"
      label="Name der Kategorie"
    >
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
        :disabled="isBusy"
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
      :disabled="isBusy"
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
      :disabled="isBusy"
      @click="isDeleteModalOpen = true"
    />
  </div>
  <CategoryDeletionModal
    v-model:open="isDeleteModalOpen"
    :category="props.category"
    :is-saving="isDeleting"
    @delete="deleteCategory"
  />
</template>
