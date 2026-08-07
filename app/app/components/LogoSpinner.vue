<script setup lang="ts">
const props = withDefaults(defineProps<{
  label?: string
  size?: number | string
  speed?: 'reload' | 'warmup'
  variant?: 'full' | 'compact'
}>(), {
  label: '',
  size: 72,
  speed: 'reload',
  variant: 'full'
})

const duration = computed(() => {
  if (props.variant === 'compact') return '0.95s'
  return props.speed === 'warmup' ? '1.8s' : '1.25s'
})
const waveDuration = computed(() => props.speed === 'warmup' ? '1.45s' : '1.05s')
</script>

<template>
  <svg
    :aria-label="label"
    :height="size"
    :style="{ '--logo-spin-duration': duration, '--logo-wave-duration': waveDuration }"
    :width="size"
    :class="['logo-spinner', { 'logo-spinner--compact': variant === 'compact' }]"
    role="img"
    viewBox="0 0 72 72"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="36"
      cy="36"
      r="27"
      :fill="variant === 'compact' ? 'var(--ui-bg)' : 'var(--ui-bg-elevated)'"
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
      v-if="variant === 'full'"
      d="M24 24c4-4 8-6 12-6s8 2 12 6"
      fill="none"
      stroke="var(--ui-text-highlighted)"
      stroke-linecap="round"
      stroke-width="4"
    />
    <path
      v-if="variant === 'full'"
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
  transform-origin: 36px 36px;
  animation: logo-spinner-rotate var(--logo-spin-duration) linear infinite;
  stroke-dasharray: 118 54;
  stroke-linecap: round;
}

.logo-spinner__wave {
  transform-origin: 36px 36px;
  animation: logo-spinner-pulse var(--logo-wave-duration) ease-in-out infinite;
}

.logo-spinner--compact .logo-spinner__ring {
  stroke-dasharray: 82 90;
}

@keyframes logo-spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}

@keyframes logo-spinner-pulse {
  0%,
  100% {
    opacity: 0.65;
    transform: scaleY(0.82);
  }

  50% {
    opacity: 1;
    transform: scaleY(1.12);
  }
}

@media (prefers-reduced-motion: reduce) {
  .logo-spinner__ring,
  .logo-spinner__wave {
    animation: none;
  }
}
</style>
