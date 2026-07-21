<script setup lang="ts">
import type { Phrase } from '~/types/speech'

defineProps<{
  phrases: Phrase[]
}>()
</script>

<template>
  <div class="grid gap-3">
    <UButton
      v-for="phrase in phrases"
      :key="phrase.number"
      class="justify-start rounded-3xl py-6 text-left"
      block
      color="neutral"
      size="xl"
      :to="{ path: '/', query: { phrase: phrase.number } }"
      variant="outline"
    >
      <span class="grid w-full grid-cols-[auto_1fr] items-center gap-4">
        <span class="text-lg font-extrabold text-slate-500">{{ phrase.number }}</span>
        <strong class="text-xl leading-snug text-slate-950">{{ phrase.text }}</strong>
      </span>
    </UButton>
  </div>
</template>
