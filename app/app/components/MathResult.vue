<script setup lang="ts">
defineProps<{
  mathText: string
  correctedText: string
}>()

defineEmits<{
  copy: []
  share: []
}>()
</script>

<template>
  <section class="space-y-4">
    <UCard>
      <p class="text-sm font-semibold text-muted">
        Mathe
      </p>
      <UButton
        class="mt-2 justify-start p-0 text-left text-4xl font-bold leading-tight"
        color="neutral"
        type="button"
        variant="link"
        @click="$emit('copy')"
      >
        {{ mathText }}
      </UButton>
      <p class="mt-3 text-base font-semibold text-muted">
        {{ correctedText }}
      </p>
    </UCard>

    <ResultActions @share="$emit('share')" />
  </section>
</template>
