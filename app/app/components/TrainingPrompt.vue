<script setup lang="ts">
defineProps<{
  index: number
  total: number
  text: string
  savedCount: number
}>()
</script>

<template>
  <div class="flex items-center justify-between gap-3 text-sm font-semibold text-muted">
    <span>Text {{ index + 1 }} von {{ total }}</span>
    <span v-if="savedCount">{{ savedCount }} gespeichert</span>
  </div>

  <UCard :ui="{ body: 'p-6 sm:p-8' }">
    <p class="text-2xl leading-relaxed font-semibold text-highlighted sm:text-3xl">
      {{ text }}
    </p>
  </UCard>
</template>
