<script setup lang="ts">
const formState = reactive({ name: '' })
const formErrors = ref<Record<string, string>>({})
const isSaving = ref(false)
const { refreshAfterCategoryChange } = usePhrases()

watch(() => formState.name, () => formErrors.value = {})

async function createCategory() {
  if (isSaving.value) return
  formErrors.value = {}
  isSaving.value = true
  try {
    const form = new FormData()
    form.append('name', formState.name)
    await $fetch('/api/categories', { method: 'POST', body: form })
    formState.name = ''
    await refreshAfterCategoryChange()
  } catch (error) {
    formErrors.value = apiFormErrors(error, 'Kategorie konnte nicht gespeichert werden.')
  } finally {
    isSaving.value = false
  }
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
