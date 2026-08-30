<script setup lang="ts">
const props = defineProps<{
  expression: string
}>()

const solution = computed(() => solveEquation(props.expression))
const hints = computed(() => equationHints(props.expression) ?? [])
const hintStep = ref(0)
const isSolutionVisible = ref(false)

watch(() => props.expression, () => {
  hintStep.value = 0
  isSolutionVisible.value = false
})

function substitute(expression: string, value: number) {
  const number = formatMathNumber(value)
  return expression
    .replace(/(\d)\s*x/gu, `$1 · ${number}`)
    .replaceAll('x', `(${number})`)
}
</script>

<template>
  <UAlert
    v-if="!solution"
    color="warning"
    icon="i-lucide-circle-alert"
    title="Diese Gleichung kann ich noch nicht lösen."
    description="Nutze eine lineare oder quadratische Gleichung mit x, zum Beispiel 2x + 3 = 11."
  />

  <UCard
    v-else
    :ui="{ body: 'space-y-4' }"
  >
    <h2 class="text-xl font-bold text-highlighted">
      Gleichung lösen
    </h2>

    <template v-if="!isSolutionVisible">
      <UButton
        v-if="hintStep < hints.length"
        block
        class="min-h-20"
        icon="i-lucide-lightbulb"
        size="xl"
        type="button"
        variant="soft"
        @click="hintStep++"
      >
        {{ hintStep ? 'Nächsten Tipp anzeigen' : 'Tipp anzeigen' }}
      </UButton>
      <ol
        v-if="hintStep"
        class="space-y-3"
      >
        <li
          v-for="(hint, index) in hints.slice(0, hintStep)"
          :key="hint"
          class="flex items-start gap-3 rounded-2xl bg-muted p-4"
        >
          <span class="flex size-8 shrink-0 items-center justify-center rounded-full bg-inverted font-bold text-inverted">
            {{ index + 1 }}
          </span>
          <p class="pt-1 font-semibold text-default">
            {{ hint }}
          </p>
        </li>
      </ol>
      <UButton
        block
        class="min-h-20"
        icon="i-lucide-eye"
        size="xl"
        type="button"
        @click="isSolutionVisible = true"
      >
        Lösung anzeigen
      </UButton>
    </template>

    <template v-else-if="solution.kind === 'solutions'">
      <div>
        <p class="font-semibold text-toned">
          Lösung{{ solution.solutions.length > 1 ? 'en' : '' }}
        </p>
        <p class="text-lg font-bold text-default">
          <span
            v-for="value in solution.solutions"
            :key="value"
            class="mr-4 inline-block"
          >x = {{ formatMathNumber(value) }}</span>
        </p>
      </div>

      <div>
        <p class="font-semibold text-toned">
          Probe
        </p>
        <p class="text-lg font-bold text-default">
          <span
            v-for="value in solution.solutions"
            :key="value"
            class="mr-4 inline-block"
          >Für x = {{ formatMathNumber(value) }}: {{ substitute(solution.left, value) }} = {{ substitute(solution.right, value) }}</span>
        </p>
      </div>
    </template>

    <p
      v-else-if="solution.kind === 'identity'"
      class="text-lg font-bold text-default"
    >
      Die Gleichung gilt für jedes x.
    </p>
    <p
      v-else
      class="text-lg font-bold text-default"
    >
      Die Gleichung hat keine reelle Lösung.
    </p>
  </UCard>
</template>
