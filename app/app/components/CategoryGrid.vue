<script setup lang="ts">
import type { Category } from '~/types/speech'

defineProps<{
  categories: Category[]
}>()
</script>

<template>
  <div class="grid grid-cols-1 gap-3">
    <UButton
      v-for="category in categories"
      :key="category.id"
      class="min-h-28 justify-center rounded-3xl text-2xl font-extrabold"
      block
      color="neutral"
      size="xl"
      :to="`/phrases/${encodeURIComponent(category.name)}`"
      variant="subtle"
    >
      {{ category.name }}
    </UButton>
  </div>
</template>
