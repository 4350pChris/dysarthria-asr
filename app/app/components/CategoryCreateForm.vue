<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Category } from '~/types/speech'

type CategoryFormState = { name: string }

defineProps<{
  autofocus?: boolean
}>()

const formState = reactive<CategoryFormState>({ name: '' })
const { refreshAfterCategoryChange } = usePhrases()
const { track } = useUsageAnalytics()
const { clearErrors, formErrors, isSaving, submit } = useFormSubmission<CategoryFormState>('Kategorie konnte nicht gespeichert werden.')
const emit = defineEmits<{
  created: [category: Category]
}>()

watch(() => formState.name, clearErrors)

async function createCategory(event: FormSubmitEvent<CategoryFormState>) {
  const category = await submit(event, data => $fetch<Category>('/api/categories', { method: 'POST', body: data }))
  if (!category) return
  track('category_created')
  formState.name = ''
  await refreshAfterCategoryChange()
  emit('created', category)
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
        :autofocus="autofocus"
        class="w-full"
        size="xl"
        placeholder="z. B. Familie"
      />
    </UFormField>
    <UButton
      class="justify-center"
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
