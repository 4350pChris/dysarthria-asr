<script setup lang="ts">
const isVisible = ref(false)

function isStandalone() {
  const navigatorWithStandalone = navigator as Navigator & { standalone?: boolean }
  return window.matchMedia('(display-mode: standalone)').matches
    || navigatorWithStandalone.standalone === true
}

function dismiss() {
  localStorage.setItem('pwa-install-hint-dismissed', 'true')
  isVisible.value = false
}

onMounted(() => {
  const isIPhone = /iPhone|iPad|iPod/.test(navigator.userAgent)
  const isSafari = /Safari/.test(navigator.userAgent)
    && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(navigator.userAgent)
  isVisible.value = isIPhone
    && isSafari
    && !isStandalone()
    && localStorage.getItem('pwa-install-hint-dismissed') !== 'true'
})
</script>

<template>
  <UAlert
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
  </UAlert>
</template>
