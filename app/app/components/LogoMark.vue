<script setup lang="ts">
withDefaults(defineProps<{
  label?: string
  size?: number | string
  state?: 'idle' | 'recording' | 'warming'
}>(), {
  label: undefined,
  size: 72,
  state: 'idle'
})
</script>

<template>
  <svg
    :aria-hidden="label ? undefined : 'true'"
    :aria-label="label"
    :height="size"
    :role="label ? 'img' : undefined"
    :width="size"
    class="group logo-mark"
    :data-active="state !== 'idle' ? '' : undefined"
    :data-state="state"
    viewBox="0 0 72 72"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      class="logo-mark__ring group-data-[active]:[stroke-dasharray:118_52] group-data-[active]:animate-spin group-data-[active]:[animation-delay:440ms] group-data-[state=warming]:[animation-duration:1.8s]"
      cx="36"
      cy="36"
      r="27"
      fill="var(--ui-bg-elevated)"
      stroke="var(--ui-primary)"
      stroke-width="4"
    />
    <path
      class="logo-mark__curve group-data-[active]:-translate-y-1 group-data-[active]:opacity-0"
      d="M24 24c4-4 8-6 12-6s8 2 12 6"
      fill="none"
      stroke="var(--ui-text-highlighted)"
      stroke-linecap="round"
      stroke-width="4"
    />
    <path
      class="logo-mark__curve group-data-[active]:translate-y-1 group-data-[active]:opacity-0"
      d="M24 48c4 4 8 6 12 6s8-2 12-6"
      fill="none"
      stroke="var(--ui-text-highlighted)"
      stroke-linecap="round"
      stroke-width="4"
    />
    <path
      class="logo-mark__wave"
      d="M27 34v4m6-8v12m6-12v12m6-8v4"
      fill="none"
      stroke="var(--ui-primary)"
      stroke-linecap="round"
      stroke-width="4"
    />
  </svg>
</template>

<style scoped>
.logo-mark__ring {
  transform-origin: 36px 36px;
  stroke-dasharray: 170 0;
  transition: stroke-dasharray 440ms ease;
}

.logo-mark__curve {
  transform-origin: 36px 36px;
  transition: opacity 380ms ease, transform 440ms ease;
}

.logo-mark:not([data-state='idle']) .logo-mark__wave {
  animation: logo-mark-pulse 1.05s ease-in-out infinite;
  transform-origin: 36px 36px;
}

.logo-mark[data-state='warming'] .logo-mark__wave {
  animation-duration: 1.45s;
}

@keyframes logo-mark-pulse {
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
  .logo-mark__ring,
  .logo-mark__curve {
    transition: none;
  }

  .logo-mark[data-active] .logo-mark__ring,
  .logo-mark:not([data-state='idle']) .logo-mark__wave {
    animation: none;
  }
}
</style>
