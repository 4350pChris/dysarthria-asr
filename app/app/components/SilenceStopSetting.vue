<script setup lang="ts">
const enabled = defineModel<boolean>({ required: true })
</script>

<template>
  <div class="flex justify-center">
    <UCheckbox
      v-model="enabled"
      label="Bei Stille automatisch stoppen"
      size="lg"
    />
  </div>
</template>
