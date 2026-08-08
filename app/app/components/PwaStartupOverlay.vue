<script setup lang="ts">
import { gsap } from 'gsap'

const isVisible = ref(true)
const overlay = useTemplateRef('overlay')
const logo = useTemplateRef('logo')
const { isTargetReady } = useStartupLogoTransition()

let animation: gsap.core.Timeline | undefined

function finish() {
  isTargetReady.value = true
  isVisible.value = false
}

onMounted(async () => {
  await nextTick()

  const target = document.querySelector<HTMLElement>('[data-startup-logo-target]')
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reducedMotion || !overlay.value || !logo.value || !target) {
    finish()
    return
  }

  const sourceBounds = logo.value.getBoundingClientRect()
  const targetBounds = target.getBoundingClientRect()
  const scale = targetBounds.width / sourceBounds.width
  const x = targetBounds.left + targetBounds.width / 2 - (sourceBounds.left + sourceBounds.width / 2)
  const y = targetBounds.top + targetBounds.height / 2 - (sourceBounds.top + sourceBounds.height / 2)
  const sourceX = sourceBounds.left + sourceBounds.width / 2
  const sourceY = sourceBounds.top + sourceBounds.height / 2
  const revealX = targetBounds.left + targetBounds.width / 2
  const revealY = targetBounds.top + targetBounds.height / 2

  animation = gsap.timeline({
    delay: 0.18,
    onComplete: finish
  })
    .set(overlay.value, {
      '--startup-reveal-x': `${sourceX}px`,
      '--startup-reveal-y': `${sourceY}px`
    })
    .to(logo.value, {
      duration: 0.62,
      ease: 'power3.inOut',
      scale,
      x,
      y
    })
    .to(overlay.value, {
      ['--startup-reveal-x']: `${revealX}px`,
      ['--startup-reveal-y']: `${revealY}px`,
      duration: 0.62,
      ease: 'power3.inOut'
    }, '<')
    .set(target, { opacity: 1 })
    .to(logo.value, {
      duration: 0.16,
      ease: 'power1.out',
      opacity: 0
    })
    .to(overlay.value, {
      autoAlpha: 0,
      duration: 0.32,
      ease: 'power2.out'
    }, '<0.04')
})

onBeforeUnmount(() => animation?.kill())
</script>

<template>
  <div
    v-if="isVisible"
    ref="overlay"
    class="startup-overlay fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 text-highlighted"
    role="status"
    aria-busy="true"
    aria-live="polite"
  >
    <div
      ref="logo"
      class="will-change-transform"
    >
      <LogoMark
        label="Sprechen wird geladen"
        :size="112"
      />
    </div>
  </div>
</template>

<style scoped>
.startup-overlay {
  --startup-reveal-x: 50%;
  --startup-reveal-y: 50%;
  background: radial-gradient(
    circle 15rem at var(--startup-reveal-x) var(--startup-reveal-y),
    color-mix(in oklab, var(--ui-primary) 12%, transparent),
    transparent 72%
  ), var(--ui-bg);
}
</style>
