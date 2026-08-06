<script setup lang="ts">
const route = useRoute()
const initialText = computed(() => String(route.query.text || ''))

definePageMeta({
  pageHeader: {
    eyebrow: 'Satz speichern',
    title: 'Satz korrigieren',
    showBack: true
  }
})
</script>

<template>
  <SaveCorrectedPhrase :initial-text="initialText" />
</template>
