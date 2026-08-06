<script setup lang="ts">
withDefaults(defineProps<{
  markSize?: number | string
}>(), {
  markSize: 52
})
</script>

<template>
  <div class="flex items-center gap-3">
    <LogoMark
      :size="markSize"
      label="Dysarthria ASR Tuned Listener"
    />
    <div class="min-w-0 leading-tight">
      <p class="font-display text-lg font-bold text-highlighted">
        Dysarthria ASR
      </p>
    </div>
  </div>
</template>
