<script setup lang="ts">
definePageMeta({
  pageHeader: {
    eyebrow: 'Persönliches ASR-Training',
    title: 'Lesetraining',
    showBack: true
  }
})
</script>

<template>
  <section class="flex flex-1 flex-col gap-5">
    <TrainingReader />
  </section>
</template>
