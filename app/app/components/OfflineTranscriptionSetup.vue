<script setup lang="ts">
const offline = useOfflineTranscription()

const label = computed(() => {
  if (offline.state.value === 'loading') return `Offline-Modell lädt: ${offline.progress.value}%`
  if (offline.isReady.value) return 'Offline-Erkennung ist bereit'
  return 'Offline-Erkennung laden (ca. 57 MB)'
})
</script>

<template>
  <section class="rounded-xl border border-default p-4">
    <p class="text-sm text-toned">
      {{ offline.isReady.value ? 'Textmodus arbeitet ohne Internet.' : 'Für Offline-Textmodus wird ein Modell einmal geladen.' }}
    </p>
    <UButton
      class="mt-3"
      :disabled="!offline.isSupported.value || offline.state.value === 'loading' || offline.isReady.value"
      icon="i-lucide-download"
      :loading="offline.state.value === 'loading'"
      type="button"
      variant="soft"
      @click="offline.prepare"
    >
      {{ label }}
    </UButton>
    <p
      v-if="offline.error.value"
      class="mt-2 text-sm text-error"
    >
      {{ offline.error.value }}
    </p>
  </section>
</template>
