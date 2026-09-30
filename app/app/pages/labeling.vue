<script setup lang="ts">
definePageMeta({
  pageHeader: {
    eyebrow: 'Audio-Labels',
    showBack: true,
    title: 'Aufnahmen prüfen'
  }
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap gap-3">
      <UButton
        color="neutral"
        icon="i-lucide-upload"
        size="lg"
        to="/whatsapp-import"
      >
        WhatsApp-Audios importieren
      </UButton>
      <UButton
        color="primary"
        external
        icon="i-lucide-download"
        size="lg"
        to="/api/labeling/training-data.zip"
      >
        Training-ZIP laden
      </UButton>
    </div>

    <LabelingWorkspace />
  </div>
</template>
