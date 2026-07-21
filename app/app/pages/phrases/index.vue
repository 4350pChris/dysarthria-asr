<script setup lang="ts">
const status = ref('')
const categories = ref<string[]>([])

onMounted(async () => {
  try {
    categories.value = (await usePhrases()).categories
  } catch {
    status.value = 'Phrasen konnten nicht geladen werden.'
  }
})
</script>

<template>
  <UMain class="min-h-dvh bg-slate-50 px-4 py-5 text-slate-950">
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
        <p class="text-sm font-semibold text-slate-500">
          Satz auswählen
        </p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          Wobei brauchst du Hilfe?
        </h1>
      </header>

      <p
        v-if="status"
        class="text-lg font-semibold text-slate-600"
      >
        {{ status }}
      </p>

      <CategoryGrid :categories="categories" />
    </UContainer>
  </UMain>
</template>
