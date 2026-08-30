<script setup lang="ts">
const mode = ref<'math'>('math')
const speech = useSpeechSession(mode)
const expression = ref('')
const result = computed(() => {
  try {
    return calculateMathExpression(expression.value)
  } catch {
    return undefined
  }
})
const hasGraph = computed(() => isGraphExpression(expression.value))

watch(() => speech.result.value?.math_text, (value) => {
  if (value) expression.value = value
})

function startRecording() {
  if (!speech.isRecording.value && !speech.isBusy.value) {
    void speech.startRecording()
  }
}

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
  <div class="flex flex-1 flex-col gap-5">
    <RecordControl
      :is-recording="speech.isRecording.value"
      :is-busy="speech.isBusy.value"
      @start="startRecording"
      @stop="speech.stopRecording"
    />

    <p
      aria-live="polite"
      class="min-h-7 text-center text-lg font-semibold text-toned"
      role="status"
    >
      {{ speech.status.value }}
    </p>

    <UCard class="space-y-4">
      <div>
        <label
          class="text-sm font-semibold text-muted"
          for="math-expression"
        >Ausdruck</label>
        <UInput
          id="math-expression"
          v-model="expression"
          class="mt-2"
          placeholder="Zum Beispiel: y = 2x + 3"
          size="xl"
        />
      </div>

      <div
        v-if="result"
        aria-live="polite"
      >
        <p class="text-sm font-semibold text-muted">
          Ergebnis
        </p>
        <p class="mt-1 text-4xl font-bold">
          {{ result }}
        </p>
      </div>

      <p
        v-else-if="expression && !hasGraph"
        class="font-semibold text-muted"
      >
        Der Ausdruck kann nicht berechnet werden.
      </p>

      <div
        v-if="expression"
        class="grid grid-cols-3 gap-3"
      >
        <UButton
          class="min-h-20 justify-center font-extrabold"
          icon="i-lucide-volume-2"
          size="xl"
          type="button"
          @click="speak"
        >
          Vorlesen
        </UButton>
        <UButton
          class="min-h-20 justify-center font-extrabold"
          icon="i-lucide-copy"
          size="xl"
          type="button"
          variant="soft"
          @click="copy"
        >
          Kopieren
        </UButton>
        <UButton
          class="min-h-20 justify-center font-extrabold"
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

    <ClientOnly>
      <MathGraph
        v-if="hasGraph"
        :expression="expression"
      />
    </ClientOnly>
  </div>
</template>
