<script setup lang="ts">
import type { Suggestion } from '~/types/speech'

defineProps<{
  selected?: Suggestion
}>()

defineEmits<{
  copy: []
  share: []
}>()

function confidence(suggestion?: Suggestion) {
  return suggestion ? Math.round(suggestion.score * 100) : 0
}

function sourceLabel(suggestion?: Suggestion) {
  if (!suggestion) return ''
  if (suggestion.source === 'generated') return 'Baustein'
  if (suggestion.source === 'emoji') return 'Emoji erkannt'
  return 'Gespeichert'
}
</script>

<template>
  <section class="space-y-4">
    <UCard>
      <p class="text-sm font-semibold text-muted">
        Vorschlag {{ confidence(selected) }}%
        <span v-if="selected"> · {{ sourceLabel(selected) }}</span>
      </p>
      <UButton
        class="mt-2 justify-start p-0 text-left text-3xl font-bold leading-tight"
        color="neutral"
        :disabled="!selected"
        type="button"
        variant="link"
        @click="$emit('copy')"
      >
        {{ selected?.text || "Kein Vorschlag" }}
      </UButton>
    </UCard>

    <UButton
      block
      class="min-h-20 justify-center rounded-2xl text-lg font-extrabold"
      color="primary"
      icon="i-lucide-pencil-line"
      label="Satz korrigieren und speichern"
      size="xl"
      :to="{ path: '/phrases/new', query: { text: selected?.text } }"
      :disabled="!selected"
    />

    <ResultActions
      :disabled="!selected"
      @share="$emit('share')"
    />
  </section>
</template>
