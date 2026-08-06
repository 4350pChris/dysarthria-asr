<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Category } from '~/types/speech'

type CategoryFormState = { name: string }

const formState = reactive<CategoryFormState>({ name: '' })
const { refreshAfterCategoryChange } = usePhrases()
const { clearErrors, formErrors, isSaving, submit } = useFormSubmission<CategoryFormState>('Kategorie konnte nicht gespeichert werden.')

watch(() => formState.name, clearErrors)

async function createCategory(event: FormSubmitEvent<CategoryFormState>) {
  if (!await submit(event, data => $fetch<Category>('/api/categories', { method: 'POST', body: data }))) return
  formState.name = ''
  await refreshAfterCategoryChange()
}
</script>

<template>
  <UForm
    :state="formState"
    class="space-y-3"
    @submit="createCategory"
  >
    <UFormField
      :error="formErrors.name || formErrors._form"
      label="Neue Kategorie"
    >
      <UInput
        v-model="formState.name"
        class="w-full"
        size="xl"
        placeholder="z. B. Familie"
      />
    </UFormField>
    <UButton
      class="min-h-16 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="primary"
      icon="i-lucide-plus"
      label="Kategorie hinzufügen"
      size="xl"
      type="submit"
      :loading="isSaving"
    />
  </UForm>
</template>
