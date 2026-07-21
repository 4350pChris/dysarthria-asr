<script setup lang="ts">
import type { Phrase } from '~/types/speech'

const route = useRoute()
const category = computed(() => decodeURIComponent(String(route.params.category || '')))
const status = ref('')
const phrases = ref<Phrase[]>([])

onMounted(async () => {
  try {
    phrases.value = (await usePhrases()).byCategory(category.value)
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
        to="/phrases"
        variant="ghost"
      >
        Kategorien
      </UButton>

      <header>
        <p class="text-sm font-semibold text-slate-500">
          Satz auswählen
        </p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          {{ category }}
        </h1>
      </header>

      <p
        v-if="status"
        class="text-lg font-semibold text-slate-600"
      >
        {{ status }}
      </p>

      <PhraseGrid :phrases="phrases" />
    </UContainer>
  </UMain>
</template>
