<script setup lang="ts">
const props = defineProps<{
  expression: string
}>()

const study = computed(() => studyFunction(props.expression))
</script>

<template>
  <UCard
    v-if="study"
    :ui="{ body: 'space-y-4' }"
  >
    <div>
      <h2 class="text-xl font-bold text-highlighted">
        Funktion untersuchen
      </h2>
      <p class="text-sm text-muted">
        Ergebnisse im Bereich von −10 bis 10.
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <div>
        <p class="font-semibold text-toned">
          Ableitung
        </p>
        <p class="text-lg font-bold text-default">
          f′(x) = {{ study.derivative }}
        </p>
      </div>
      <div v-if="study.yIntercept !== undefined">
        <p class="font-semibold text-toned">
          y-Achsenabschnitt
        </p>
        <p class="text-lg font-bold text-default">
          (0 | {{ formatMathNumber(study.yIntercept) }})
        </p>
      </div>
      <div>
        <p class="font-semibold text-toned">
          Nullstellen
        </p>
        <p class="text-lg font-bold text-default">
          <template v-if="study.roots.length">
            <span
              v-for="root in study.roots"
              :key="root"
              class="mr-3 inline-block"
            >( {{ formatMathNumber(root) }} | 0 )</span>
          </template>
          <template v-else>
            Keine im Bereich
          </template>
        </p>
      </div>
      <div>
        <p class="font-semibold text-toned">
          Extrempunkte
        </p>
        <p class="text-lg font-bold text-default">
          <template v-if="study.extrema.length">
            <span
              v-for="point in study.extrema"
              :key="`${point.kind}-${point.x}`"
              class="mr-3 inline-block"
            >{{ point.kind }} ({{ formatMathNumber(point.x) }} | {{ formatMathNumber(point.y) }})</span>
          </template>
          <template v-else>
            Keine im Bereich
          </template>
        </p>
      </div>
    </div>
  </UCard>
</template>
