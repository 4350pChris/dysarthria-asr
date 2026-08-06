<script setup lang="ts">
defineProps<{
  open: boolean
}>()
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-default/95 text-highlighted"
    role="alert"
    aria-busy="true"
    aria-live="assertive"
  >
    <UIcon
      class="size-12 animate-spin text-primary"
      name="i-lucide-loader-circle"
    />
    <p class="text-lg font-bold">
      Aktualisierung wird geladen
    </p>
  </div>
</template>
