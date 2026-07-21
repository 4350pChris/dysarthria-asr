<script setup lang="ts">
defineProps<{
  categories: string[]
}>()
</script>

<template>
  <div class="grid grid-cols-1 gap-3">
    <UButton
      v-for="category in categories"
      :key="category"
      class="min-h-28 justify-center rounded-3xl text-2xl font-extrabold"
      block
      color="neutral"
      size="xl"
      :to="`/phrases/${encodeURIComponent(category)}`"
      variant="subtle"
    >
      {{ category }}
    </UButton>
  </div>
</template>
