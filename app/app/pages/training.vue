<script setup lang="ts">
const speechCommands = useSpeechCommands()

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
    <SpeechCommandControl
      :is-listening="speechCommands.isListening.value"
      :is-supported="speechCommands.isSupported.value"
      :status="speechCommands.status.value"
      @start="speechCommands.start"
      @stop="speechCommands.stop"
    />

    <TrainingReader />
  </section>
</template>
