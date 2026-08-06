<script setup lang="ts">
const props = withDefaults(defineProps<{
  label?: string
  size?: number | string
  speed?: 'reload' | 'warmup'
}>(), {
  label: 'Lädt',
  size: 72,
  speed: 'reload'
})

const duration = computed(() => props.speed === 'warmup' ? '4.8s' : '1.1s')
const waveDuration = computed(() => props.speed === 'warmup' ? '2.4s' : '1.4s')
</script>

<template>
  <svg
    :aria-label="label"
    :height="size"
    :style="{ '--logo-spin-duration': duration, '--logo-wave-duration': waveDuration }"
    :width="size"
    class="logo-spinner"
    role="img"
    viewBox="0 0 72 72"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="36"
      cy="36"
      r="27"
      fill="var(--ui-bg-elevated)"
      stroke="var(--ui-border)"
      stroke-width="4"
    />
    <circle
      class="logo-spinner__ring"
      cx="36"
      cy="36"
      r="27"
      fill="none"
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
      class="logo-spinner__wave"
      d="M27 34v4m6-8v12m6-12v12m6-8v4"
      fill="none"
      stroke="var(--ui-primary)"
      stroke-linecap="round"
      stroke-width="4"
    />
  </svg>
</template>

<style scoped>
.logo-spinner__ring {
  transform-box: fill-box;
  transform-origin: center;
  animation: logo-spinner-rotate var(--logo-spin-duration) linear infinite;
}

.logo-spinner__wave {
  transform-box: fill-box;
  transform-origin: center;
  animation: logo-spinner-pulse var(--logo-wave-duration) ease-in-out infinite;
}

@keyframes logo-spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}

@keyframes logo-spinner-pulse {
  50% {
    opacity: 0.55;
    transform: scaleY(0.82);
  }
}

@media (prefers-reduced-motion: reduce) {
  .logo-spinner__ring,
  .logo-spinner__wave {
    animation: none;
  }
}
</style>
