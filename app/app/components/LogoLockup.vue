<script setup lang="ts">
withDefaults(defineProps<{
  markSize?: number | string
}>(), {
  markSize: 52
})
</script>

<template>
  <div class="shrink-0 flex items-center gap-3">
    <LogoMark
      :size="markSize"
      label="Dysarthria ASR Tuned Listener"
    />
    <div class="leading-tight">
      <p class="font-display whitespace-nowrap text-lg font-bold text-highlighted">
        Dysarthria ASR
      </p>
    </div>
  </div>
</template>
