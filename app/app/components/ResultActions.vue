<script setup lang="ts">
defineProps<{
  disabled?: boolean
}>()

defineEmits<{
  shareInstagram: []
  shareText: []
}>()
</script>

<template>
  <div class="grid grid-cols-2 gap-3">
    <UButton
      class="min-h-24 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="primary"
      icon="i-lucide-volume-2"
      label="Vorlesen"
      size="xl"
      type="submit"
      :disabled="disabled"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
    />
    <UButton
      class="min-h-24 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="secondary"
      icon="i-lucide-instagram"
      label="Instagram"
      size="xl"
      type="button"
      :disabled="disabled"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
      @click="$emit('shareInstagram')"
    />
    <UButton
      class="col-span-2 min-h-20 justify-center rounded-2xl text-lg font-extrabold"
      block
      color="neutral"
      icon="i-lucide-share-2"
      label="Text teilen"
      size="xl"
      type="button"
      :disabled="disabled"
      variant="subtle"
      :ui="{ leadingIcon: 'size-7' }"
      @click="$emit('shareText')"
    />
  </div>
</template>
