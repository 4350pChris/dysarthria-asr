<script setup lang="ts">
import type { Suggestion } from '~/types/speech'

defineProps<{
  selected?: Suggestion
}>()

function confidence(suggestion?: Suggestion) {
  return suggestion ? Math.round(suggestion.score * 100) : 0
}
</script>

<template>
  <section class="space-y-4">
    <UCard>
      <p class="text-sm font-semibold text-slate-500">
        Vorschlag {{ confidence(selected) }}%
      </p>
      <p class="mt-2 text-3xl font-bold leading-tight">
        {{ selected?.text || "Kein Vorschlag" }}
      </p>
    </UCard>

    <UButton
      class="min-h-24 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="primary"
      icon="i-lucide-volume-2"
      label="Vorlesen"
      size="xl"
      type="submit"
      :disabled="!selected"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
    />
  </section>
</template>
