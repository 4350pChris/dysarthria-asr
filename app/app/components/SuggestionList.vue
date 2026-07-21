<script setup lang="ts">
import type { Suggestion } from "~/types/speech";

defineProps<{
  suggestions: Suggestion[];
  selected?: Suggestion;
}>();

defineEmits<{
  select: [suggestion: Suggestion];
}>();

function sourceLabel(suggestion: Suggestion) {
  return suggestion.source === "generated" ? "Baustein" : "Gespeichert";
}
</script>

<template>
  <section v-if="suggestions.length > 1" class="space-y-2">
    <p class="text-sm font-semibold text-muted">Andere Vorschläge</p>
    <UButton
      v-for="suggestion in suggestions"
      :key="suggestion.id"
      class="justify-start rounded-2xl py-4 text-left"
      block
      color="neutral"
      type="button"
      variant="outline"
      :class="
        selected?.id === suggestion.id
          ? 'ring-4 ring-primary/20 border-primary'
          : ''
      "
      @click="$emit('select', suggestion)"
    >
      <span class="grid w-full grid-cols-[1fr_auto] items-start gap-3">
        <span class="space-y-1">
          <strong class="block text-base text-highlighted">{{
            suggestion.text
          }}</strong>
          <small
            class="block text-xs font-bold uppercase tracking-normal text-muted"
          >
            {{ sourceLabel(suggestion) }}
          </small>
        </span>
        <small class="font-extrabold text-muted">
          {{ Math.round(suggestion.score * 100) }}%
        </small>
      </span>
    </UButton>
  </section>
</template>
