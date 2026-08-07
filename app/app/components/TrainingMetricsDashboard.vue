<script setup lang="ts">
type ModelMetrics = {
  source: string
  total: number
  scored: number
  word_error_rate: number | null
  character_error_rate: number | null
}

const { data } = await useFetch<{ models: ModelMetrics[] }>('/api/labeling/training-metrics', {
  default: () => ({ models: [] })
})

function percent(value: number | null) {
  return value === null ? '–' : `${Math.round(value * 100)} %`
}
</script>

<template>
  <section class="space-y-5">
    <UCard
      v-for="model in data.models"
      :key="model.source"
    >
      <template #header>
        <h2 class="text-lg font-extrabold">
          {{ model.source === 'server' ? 'Server-ASR' : model.source }}
        </h2>
      </template>
      <div class="grid gap-4 sm:grid-cols-3">
        <div>
          <p class="text-sm text-muted">
            Ausgewertet
          </p>
          <p class="text-2xl font-extrabold">
            {{ model.scored }} / {{ model.total }}
          </p>
        </div>
        <div>
          <p class="text-sm text-muted">
            Wortfehler
          </p>
          <p class="text-2xl font-extrabold">
            {{ percent(model.word_error_rate) }}
          </p>
        </div>
        <div>
          <p class="text-sm text-muted">
            Zeichenfehler
          </p>
          <p class="text-2xl font-extrabold">
            {{ percent(model.character_error_rate) }}
          </p>
        </div>
      </div>
    </UCard>
    <p
      v-if="!data.models.length"
      class="text-muted"
    >
      Noch keine Trainingsaufnahmen mit Text.
    </p>
  </section>
</template>
