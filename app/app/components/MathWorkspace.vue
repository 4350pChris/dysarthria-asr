<script setup lang="ts">
const props = defineProps<{
  speech: ReturnType<typeof useSpeechSession>
}>()

const speech = props.speech
const expression = ref('')
const result = computed(() => {
  try {
    return calculateMathExpression(expression.value)
  } catch {
    return undefined
  }
})
const hasGraph = computed(() => isGraphExpression(expression.value))
const hasEquation = computed(() => isEquationExpression(expression.value))
const graphRange = ref<[number, number]>([-10, 10])

watch(() => speech.result.value?.math_text, (value) => {
  if (value) expression.value = value
})

function speak() {
  if (!expression.value) return
  speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(expression.value)
  utterance.lang = 'de-DE'
  speechSynthesis.speak(utterance)
}

async function copy() {
  if (!expression.value) return
  try {
    await navigator.clipboard.writeText(expression.value)
    speech.status.value = 'Kopiert.'
  } catch {
    speech.status.value = 'Kopieren nicht möglich.'
  }
}

async function share() {
  if (!expression.value || !navigator.share) return
  try {
    await navigator.share({ text: expression.value })
  } catch {
    speech.status.value = 'Teilen abgebrochen.'
  }
}
</script>

<template>
  <div class="space-y-5">
    <UCard :ui="{ body: 'space-y-4' }">
      <div class="flex gap-3">
        <UFormField
          class="w-full"
          name="math-expression"
          label="Ausdruck"
          :error="!result && expression && !hasGraph && !hasEquation && 'Der Ausdruck kann nicht berechnet werden.'"
        >
          <UInput
            v-model="expression"
            class="mt-2 w-full"
            placeholder="Zum Beispiel: y = 2x + 3"
            size="xl"
          >
            <template
              v-if="result"
              #trailing
            >
              <p class="flex items-center gap-2">
                <span class="text-sm font-semibold text-muted">
                  =
                </span>
                <span class="text-xl font-bold">
                  {{ result }}
                </span>
              </p>
            </template>
          </UInput>
        </UFormField>
      </div>

      <div
        v-if="expression"
        class="flex flex-col md:grid grid-cols-3 gap-3"
      >
        <UButton
          block
          class="min-h-20"
          icon="i-lucide-volume-2"
          size="xl"
          type="button"
          @click="speak"
        >
          Vorlesen
        </UButton>
        <UButton
          block
          class="min-h-20"
          icon="i-lucide-copy"
          size="xl"
          type="button"
          variant="soft"
          @click="copy"
        >
          Kopieren
        </UButton>
        <UButton
          block
          class="min-h-20"
          icon="i-lucide-share-2"
          size="xl"
          type="button"
          variant="soft"
          @click="share"
        >
          Teilen
        </UButton>
      </div>
    </UCard>

    <LazyMathGraph
      v-if="hasGraph && !hasEquation"
      :expression="expression"
      @range-change="graphRange = $event"
    />
    <LazyMathFunctionStudy
      v-if="hasGraph && !hasEquation"
      :expression="expression"
      :range="graphRange"
    />
    <LazyMathEquationSolver
      v-if="hasEquation"
      :expression="expression"
    />
  </div>
</template>
