<script setup lang="ts">
const { $pwa } = useNuxtApp()
const { isSafeToUpdate } = usePwaUpdateSafety()

const isVisible = computed(() => Boolean($pwa?.needRefresh))

async function update() {
  if (!isSafeToUpdate.value) return
  await $pwa?.updateServiceWorker()
}

async function dismiss() {
  await $pwa?.cancelPrompt()
}
</script>

<template>
  <UAlert
    v-if="isVisible"
    color="primary"
    icon="i-lucide-download"
    title="Update bereit"
    :description="isSafeToUpdate ? 'Die neue Version ist bereit.' : 'Die neue Version wird nach der Aufnahme bereit sein.'"
  >
    <template #actions>
      <UButton
        color="primary"
        label="Aktualisieren"
        type="button"
        :disabled="!isSafeToUpdate"
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
