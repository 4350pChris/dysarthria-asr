<script setup lang="ts">
const props = defineProps<{
  savedCount: number
}>()

const goals = [
  { count: 3, title: 'Erste Runde' },
  { count: 5, title: 'Läuft' },
  { count: 10, title: 'Zehn voll' },
  { count: 20, title: 'Richtig gut' }
]
const nextGoal = computed(() => goals.find(goal => goal.count > props.savedCount))
const goalCopy = computed(() => {
  if (!nextGoal.value) return '20 Aufnahmen. Wow.'
  return `Noch ${nextGoal.value.count - props.savedCount} bis zu ${nextGoal.value.title}.`
})
const currentGoalIndex = computed(() => {
  const index = goals.findIndex(goal => goal.count > props.savedCount)
  return index === -1 ? goals.length - 1 : index
})
const celebration = computed(() => {
  if (props.savedCount === 10) return { title: 'Zehn voll!', message: 'Das läuft heute richtig gut.' }
  if (props.savedCount === 20) return { title: 'Zwanzig!', message: 'Wow. Das ist eine richtig starke Runde.' }
  return undefined
})
</script>

<template>
  <UCard :ui="{ body: 'p-5' }">
    <p class="text-lg font-extrabold text-highlighted">
      Schon {{ savedCount }} Aufnahmen
    </p>
    <p class="mt-1 text-sm font-semibold text-muted">
      {{ goalCopy }}
    </p>
    <UStepper
      :items="goals"
      :model-value="currentGoalIndex"
      class="mt-5"
      color="primary"
      disabled
      size="sm"
      :ui="{ title: 'whitespace-nowrap text-xs font-bold' }"
    >
      <template #indicator="{ item }">
        {{ item.count }}
      </template>
    </UStepper>
    <Transition name="celebration">
      <div
        v-if="celebration"
        class="celebration relative mt-5 overflow-hidden rounded-2xl bg-primary px-5 py-4 text-inverted"
        role="status"
      >
        <span
          v-for="spark in 5"
          :key="spark"
          aria-hidden="true"
          class="celebration-spark"
          :class="`celebration-spark-${spark}`"
        >
          ✦
        </span>
        <p class="relative text-lg font-extrabold">
          {{ celebration.title }}
        </p>
        <p class="relative text-sm font-semibold opacity-90">
          {{ celebration.message }}
        </p>
      </div>
    </Transition>
  </UCard>
</template>

<style scoped>
.celebration {
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
