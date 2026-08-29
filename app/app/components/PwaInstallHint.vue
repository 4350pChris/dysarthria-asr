<script setup lang="ts">
const isVisible = ref(false)
const isDismissed = useLocalStorage('pwa-install-hint-dismissed', false)

function isStandalone() {
  const navigatorWithStandalone = navigator as Navigator & { standalone?: boolean }
  return window.matchMedia('(display-mode: standalone)').matches
    || navigatorWithStandalone.standalone === true
}

function dismiss() {
  isDismissed.value = true
  isVisible.value = false
}

onMounted(() => {
  const isIPhone = /iPhone|iPad|iPod/.test(navigator.userAgent)
  const isSafari = /Safari/.test(navigator.userAgent)
    && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(navigator.userAgent)
  isVisible.value = isIPhone
    && isSafari
    && !isStandalone()
    && !isDismissed.value
})
</script>

<template>
  <LazyUAlert
    v-if="isVisible"
    color="primary"
    icon="i-lucide-square-plus"
    title="Zum Home-Bildschirm hinzufügen"
    description="Tippe auf Teilen und dann auf Zum Home-Bildschirm. Danach öffnet Sprechen wie eine App."
  >
    <template #actions>
      <UButton
        color="primary"
        label="Später"
        type="button"
        variant="soft"
        @click="dismiss"
      />
    </template>
  </LazyUAlert>
</template>
