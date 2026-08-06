<script setup lang="ts">
const { $pwa } = useNuxtApp()
const { isSafeToUpdate } = usePwaUpdateSafety()

const isVisible = computed(() => Boolean($pwa?.needRefresh))
const isUpdating = ref(false)
let reloadTimer: ReturnType<typeof setTimeout> | undefined

function reload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  window.location.reload()
}

async function update() {
  if (!isSafeToUpdate.value || isUpdating.value) return

  isUpdating.value = true
  navigator.serviceWorker.addEventListener('controllerchange', reload, { once: true })

  await $pwa?.updateServiceWorker()

  // Safari can activate the new worker without dispatching controllerchange.
  // Give it time to activate, then reload the page as a fallback.
  reloadTimer = setTimeout(reload, 3_000)
}

async function dismiss() {
  await $pwa?.cancelPrompt()
}
</script>

<template>
  <PwaUpdateOverlay :open="isUpdating" />

  <UAlert
    v-if="isVisible"
    color="primary"
    icon="i-lucide-download"
    title="Update bereit"
    :description="isUpdating ? 'Die neue Version wird geladen.' : isSafeToUpdate ? 'Die neue Version ist bereit.' : 'Die neue Version wird nach der Aufnahme bereit sein.'"
  >
    <template #actions>
      <UButton
        color="primary"
        label="Aktualisieren"
        type="button"
        :disabled="!isSafeToUpdate || isUpdating"
        :loading="isUpdating"
        @click="update"
      />
      <UButton
        color="neutral"
        label="Später"
        type="button"
        variant="soft"
        @click="dismiss"
      />
    </template>
  </UAlert>
</template>
