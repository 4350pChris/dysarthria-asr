<script setup lang="ts">
const route = useRoute()
const initialText = computed(() => String(route.query.text || ''))
</script>

<template>
  <UMain class="min-h-dvh bg-default px-4 py-5 text-highlighted">
    <UContainer class="max-w-md space-y-6">
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
          Satz speichern
        </p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          Satz korrigieren
        </h1>
      </header>

      <SaveCorrectedPhrase :initial-text="initialText" />
    </UContainer>
  </UMain>
</template>
