<script setup lang="ts">
defineProps<{
  mathText: string
  correctedText: string
}>()
</script>

<template>
  <section class="space-y-4">
    <UCard>
      <p class="text-sm font-semibold text-slate-500">
        Mathe
      </p>
      <p class="mt-2 text-4xl font-bold leading-tight">
        {{ mathText }}
      </p>
      <p class="mt-3 text-base font-semibold text-slate-500">
        {{ correctedText }}
      </p>
    </UCard>

    <UButton
      class="min-h-24 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="primary"
      icon="i-lucide-volume-2"
      label="Vorlesen"
      size="xl"
      type="submit"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
    />
  </section>
</template>
