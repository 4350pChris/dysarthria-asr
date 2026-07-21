<script setup lang="ts">
import type { Suggestion } from '~/types/speech'

defineProps<{
  suggestions: Suggestion[]
  selected?: Suggestion
}>()

defineEmits<{
  select: [suggestion: Suggestion]
}>()
</script>

<template>
  <section
    v-if="suggestions.length > 1"
    class="space-y-2"
  >
    <p class="text-sm font-semibold text-slate-500">
      Andere Vorschläge
    </p>
    <UButton
      v-for="suggestion in suggestions"
      :key="suggestion.phrase_number"
      class="justify-start rounded-2xl py-4 text-left"
      block
      color="neutral"
      variant="outline"
      :class="selected?.phrase_number === suggestion.phrase_number ? 'ring-4 ring-primary/20 border-primary' : ''"
      @click="$emit('select', suggestion)"
    >
      <span class="grid w-full grid-cols-[auto_1fr_auto] items-center gap-3">
        <span class="font-extrabold text-slate-500">{{ suggestion.phrase_number }}</span>
        <strong class="text-base text-slate-950">{{ suggestion.text }}</strong>
        <small class="font-extrabold text-slate-500">{{ Math.round(suggestion.score * 100) }}%</small>
      </span>
    </UButton>
  </section>
</template>
