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
  </UCard>
  <TrainingCelebration :saved-count="savedCount" />
</template>
