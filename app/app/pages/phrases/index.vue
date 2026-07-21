<script setup lang="ts">
const status = ref('')
const formState = reactive({ name: '' })
const isSaving = ref(false)
const { categories, loadPhrases } = usePhrases()

onMounted(loadCategories)

async function loadCategories() {
  try {
    await loadPhrases()
  } catch {
    status.value = 'Phrasen konnten nicht geladen werden.'
  }
}

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
    await loadPhrases({ force: true })
  } catch {
    status.value = 'Kategorie konnte nicht gespeichert werden.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <UMain class="min-h-dvh bg-default px-4 py-5 text-highlighted">
    <UContainer class="max-w-md space-y-5">
      <UButton
        class="min-h-14 rounded-2xl font-extrabold"
        color="neutral"
        icon="i-lucide-arrow-left"
        size="xl"
        to="/"
        variant="ghost"
      >
        Zurück
      </UButton>

      <header>
        <p class="text-sm font-semibold text-muted">
          Satz auswählen
        </p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          Wobei brauchst du Hilfe?
        </h1>
      </header>

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
    </UContainer>
  </UMain>
</template>
