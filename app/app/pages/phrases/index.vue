<script setup lang="ts">
const status = ref('')
const formState = reactive({ name: '' })
const isSaving = ref(false)
const { categories, refreshAfterCategoryChange } = usePhrases()

definePageMeta({
  pageHeader: {
    eyebrow: 'Satz auswählen',
    title: 'Wobei brauchst du Hilfe?',
    showBack: true
  }
})

async function createCategory() {
  const name = formState.name.trim()
  if (!name || isSaving.value) return
  isSaving.value = true
  const form = new FormData()
  form.append('name', name)
  try {
    await $fetch('/api/categories', { method: 'POST', body: form })
    formState.name = ''
    status.value = 'Kategorie gespeichert.'
    await refreshAfterCategoryChange()
  } catch {
    status.value = 'Kategorie konnte nicht gespeichert werden.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <p
      v-if="status"
      class="text-lg font-semibold text-toned"
    >
      {{ status }}
    </p>

    <UForm
      :state="formState"
      class="space-y-3"
      @submit="createCategory"
    >
      <UFormField label="Neue Kategorie">
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

    <CategoryGrid :categories="categories" />
  </div>
</template>
