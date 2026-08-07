<script setup lang="ts">
const props = defineProps<{
  savedCount: number
}>()

const celebration = ref<{ title: string, message: string }>()
let celebrationTimer: ReturnType<typeof setTimeout> | undefined

watch(() => props.savedCount, (count) => {
  const message = count === 10
    ? { title: 'Zehn voll!', message: 'Das läuft heute richtig gut.' }
    : count === 20
      ? { title: 'Zwanzig!', message: 'Wow. Das ist eine richtig starke Runde.' }
      : undefined
  if (!message) return
  clearTimeout(celebrationTimer)
  celebration.value = message
  celebrationTimer = setTimeout(() => {
    celebration.value = undefined
  }, 2_400)
})

onBeforeUnmount(() => clearTimeout(celebrationTimer))
</script>

<template>
  <Transition name="celebration">
    <div
      v-if="celebration"
      class="celebration-screen"
      role="status"
    >
      <div class="celebration relative overflow-hidden rounded-3xl bg-primary px-7 py-6 text-center text-inverted shadow-xl">
        <span
          v-for="spark in 5"
          :key="spark"
          aria-hidden="true"
          class="celebration-spark"
          :class="`celebration-spark-${spark}`"
        >
          ✦
        </span>
        <p class="relative text-2xl font-extrabold">
          {{ celebration.title }}
        </p>
        <p class="relative mt-1 text-base font-semibold opacity-90">
          {{ celebration.message }}
        </p>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.celebration-screen {
  position: fixed;
  z-index: 50;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  pointer-events: none;
  background: rgb(236 72 153 / 12%);
}

.celebration {
  max-width: 28rem;
  animation: celebration-pop 500ms cubic-bezier(.2, 1.5, .5, 1);
}

.celebration-spark {
  position: absolute;
  animation: celebration-spark 900ms ease-out both;
  font-size: 1.5rem;
  opacity: 0;
}

.celebration-spark-1 { top: 10%; left: 8%; animation-delay: 50ms; }
.celebration-spark-2 { top: 55%; left: 20%; animation-delay: 120ms; }
.celebration-spark-3 { top: 12%; right: 22%; animation-delay: 80ms; }
.celebration-spark-4 { right: 9%; bottom: 12%; animation-delay: 180ms; }
.celebration-spark-5 { right: 38%; bottom: 4%; animation-delay: 220ms; }

.celebration-enter-active,
.celebration-leave-active {
  transition: opacity 200ms ease;
}

.celebration-enter-from,
.celebration-leave-to {
  opacity: 0;
}

@keyframes celebration-pop {
  0% { transform: scale(.85); }
  70% { transform: scale(1.03); }
  100% { transform: scale(1); }
}

@keyframes celebration-spark {
  15% { opacity: 1; transform: translateY(8px) scale(.6) rotate(-20deg); }
  100% { opacity: 0; transform: translateY(-28px) scale(1.2) rotate(20deg); }
}

@media (prefers-reduced-motion: reduce) {
  .celebration,
  .celebration-spark {
    animation: none;
  }
}
</style>
