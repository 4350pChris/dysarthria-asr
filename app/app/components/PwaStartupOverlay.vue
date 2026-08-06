<script setup lang="ts">
const isVisible = ref(true)

onMounted(() => {
  requestAnimationFrame(() => {
    isVisible.value = false
  })
})
</script>

<template>
  <div
    v-if="isVisible"
    class="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-default text-highlighted"
    role="status"
    aria-busy="true"
    aria-live="polite"
  >
    <LogoSpinner
      label="Sprechen wird geladen"
      :size="112"
      speed="reload"
      variant="full"
    />
  </div>
</template>
