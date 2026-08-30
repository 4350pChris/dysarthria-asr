<script setup lang="ts">
defineProps<{ level: number }>()
</script>

<template>
  <div
    aria-label="Mikrofonpegel"
    aria-valuemax="100"
    aria-valuemin="0"
    :aria-valuenow="Math.round(level * 100)"
    class="h-3 overflow-hidden rounded-full bg-muted"
    role="meter"
  >
    <div
      class="h-full rounded-full bg-primary transition-[width] duration-100"
      :style="{ width: `${Math.round(level * 100)}%` }"
    />
  </div>
</template>
