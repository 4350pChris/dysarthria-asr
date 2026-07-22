<script setup lang="ts">
defineProps<{
  disabled?: boolean
}>()

defineEmits<{
  share: []
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
      color="success"
      icon="i-simple-icons-whatsapp"
      label="WhatsApp"
      size="xl"
      type="button"
      :disabled="disabled"
      :ui="{ leadingIcon: 'size-7', base: 'flex-col gap-1.5' }"
      @click="$emit('share')"
    />
  </div>
</template>
