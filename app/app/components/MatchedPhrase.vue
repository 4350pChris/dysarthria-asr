<script setup lang="ts">
import type { Suggestion } from '~/types/speech'

defineProps<{
  selected?: Suggestion
}>()

defineEmits<{
  speak: []
  reset: []
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
        {{ selected?.text || 'Kein Vorschlag' }}
      </p>
    </UCard>

    <div class="grid grid-cols-2 gap-3">
      <UButton
        class="min-h-24 justify-center rounded-2xl text-lg font-extrabold"
        block
        color="primary"
        icon="i-lucide-volume-2"
        size="xl"
        :disabled="!selected"
        :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
        @click="$emit('speak')"
      >
        Vorlesen
      </UButton>
      <UButton
        class="min-h-24 justify-center rounded-2xl text-lg font-extrabold"
        block
        color="neutral"
        icon="i-lucide-rotate-ccw"
        size="xl"
        variant="subtle"
        :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
        @click="$emit('reset')"
      >
        Nochmal
      </UButton>
    </div>
  </section>
</template>
