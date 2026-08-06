<script setup lang="ts">
withDefaults(defineProps<{
  label?: string
  size?: number | string
}>(), {
  label: undefined,
  size: 72
})
</script>

<template>
  <svg
    :aria-hidden="label ? undefined : 'true'"
    :aria-label="label"
    :height="size"
    :role="label ? 'img' : undefined"
    :width="size"
    viewBox="0 0 72 72"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="36"
      cy="36"
      r="27"
      fill="var(--ui-bg-elevated)"
      stroke="var(--ui-primary)"
      stroke-width="4"
    />
    <path
      d="M24 24c4-4 8-6 12-6s8 2 12 6"
      fill="none"
      stroke="var(--ui-text-highlighted)"
      stroke-linecap="round"
      stroke-width="4"
    />
    <path
      d="M24 48c4 4 8 6 12 6s8-2 12-6"
      fill="none"
      stroke="var(--ui-text-highlighted)"
      stroke-linecap="round"
      stroke-width="4"
    />
    <path
      d="M27 34v4m6-8v12m6-12v12m6-8v4"
      fill="none"
      stroke="var(--ui-primary)"
      stroke-linecap="round"
      stroke-width="4"
    />
  </svg>
</template>
