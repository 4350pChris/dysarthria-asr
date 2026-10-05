<script setup lang="ts">
type Issue = { original: string, replacement: string, start: number, number: number }

const props = defineProps<{ text: string, audioId?: string, disabled?: boolean, inactive?: boolean }>()
const emit = defineEmits<{ updateText: [text: string], active: [active: boolean] }>()
const commands = useSpeechCommands()
const issues = ref<Issue[]>([])
const current = ref<Issue>()
const reviewOpen = ref(false)
const reviewTotal = ref(0)
const actionLocked = refAutoReset(false, 2_000)
const checking = ref(false)
const editing = ref(false)
const status = ref('')
const undo = ref<{ before: string, after: string, issues: Issue[], current?: Issue }>()
let snapshot = props.text
let expectedText: string | undefined
let request: AbortController | undefined
function edit() {
  if (props.disabled || props.inactive || reviewOpen.value) return
  editing.value = true
}

watch(reviewOpen, value => emit('active', value), { flush: 'sync' })

const parts = computed(() => {
  const parts: Array<{ text: string, number?: number }> = []
  let offset = 0
  for (const issue of issues.value) {
    parts.push({ text: props.text.slice(offset, issue.start) })
    parts.push({ text: issue.original, number: issue.number })
    offset = issue.start + issue.original.length
  }
  parts.push({ text: props.text.slice(offset) })
  return parts
})
const context = computed(() => {
  const issue = current.value
  if (!issue) return
  // ponytail: punctuation splits sentences; use a German segmenter if abbreviations cause trouble.
  const sentence = [...props.text.matchAll(/[^.!?\n]+(?:[.!?]+|$)/g)]
    .find(match => issue.start >= match.index && issue.start < match.index + match[0].length)
  return {
    before: props.text.slice(sentence ? sentence.index + sentence[0].indexOf(sentence[0].trim()) : issue.start, issue.start),
    after: props.text.slice(issue.start + issue.original.length, Math.max(issue.start + issue.original.length, sentence ? sentence.index + sentence[0].trimEnd().length : 0))
  }
})

watch(() => [props.text, props.audioId, props.disabled] as const, ([text, audioId, disabled], previous) => {
  if (text === expectedText && audioId === previous?.[1] && !disabled) {
    snapshot = text
    expectedText = undefined
    return
  }
  request?.abort()
  snapshot = text
  expectedText = undefined
  issues.value = []
  current.value = undefined
  reviewOpen.value = false
  actionLocked.value = false
  if (audioId !== previous?.[1] || disabled) editing.value = false
  undo.value = undefined
  status.value = ''
  checking.value = false
  if (audioId && !disabled && (audioId !== previous?.[1] || previous?.[2])) void check()
}, { immediate: true })

async function check() {
  if (props.disabled || checking.value || !props.text.trim()) return
  request?.abort()
  const controller = new AbortController()
  request = controller
  const text = props.text
  snapshot = text
  checking.value = true
  status.value = 'Text wird geprüft …'
  try {
    const result = await $fetch<{ suggestions: Array<{ original: string, replacement: string }> }>('/api/transcript/review', {
      method: 'POST', body: { text }, signal: controller.signal
    })
    if (controller.signal.aborted || props.text !== text) return
    issues.value = result.suggestions.map((issue, index) => ({ ...issue, start: text.indexOf(issue.original), number: index + 1 }))
    status.value = issues.value.length ? `${issues.value.length} ${issues.value.length === 1 ? 'Stelle' : 'Stellen'} bitte prüfen. Sage „Prüfen“.` : 'Keine auffällige Stelle gefunden. Fehler können trotzdem vorkommen.'
  } catch {
    if (!controller.signal.aborted) status.value = 'Textprüfung nicht verfügbar. Du kannst den Text direkt bearbeiten.'
  } finally {
    if (request === controller) checking.value = false
  }
}

function review() {
  if (props.disabled || props.inactive) return
  if (issues.value.length) {
    current.value = issues.value[0]
    reviewTotal.value = Math.max(...issues.value.map(issue => issue.number))
    reviewOpen.value = true
    commands.speak('')
    status.value = 'Sage „Übernehmen“ oder „Behalten“.'
  } else void check()
}

function keep() {
  if (!current.value || props.disabled || actionLocked.value) return
  actionLocked.value = true
  undo.value = { before: props.text, after: props.text, issues: [...issues.value], current: current.value }
  issues.value = issues.value.filter(issue => issue !== current.value)
  current.value = issues.value[0]
  status.value = 'Original behalten.'
}

function apply() {
  const issue = current.value
  if (!issue?.replacement || props.disabled || actionLocked.value) return
  if (props.text !== snapshot || props.text.slice(issue.start, issue.start + issue.original.length) !== issue.original) return
  const text = props.text.slice(0, issue.start) + issue.replacement + props.text.slice(issue.start + issue.original.length)
  actionLocked.value = true
  undo.value = { before: props.text, after: text, issues: [...issues.value], current: issue }
  issues.value = issues.value.filter(item => item.start + item.original.length <= issue.start || item.start >= issue.start + issue.original.length).map(item => ({
    ...item, start: item.start > issue.start ? item.start + issue.replacement.length - issue.original.length : item.start
  }))
  current.value = issues.value[0]
  expectedText = text
  emit('updateText', text)
  status.value = 'Änderung übernommen.'
}

function restore() {
  if (!undo.value || props.text !== undo.value.after || props.disabled) return
  const text = undo.value.before
  issues.value = undo.value.issues
  current.value = reviewOpen.value ? undo.value.current : undefined
  actionLocked.value = false
  expectedText = text
  undo.value = undefined
  emit('updateText', text)
  status.value = 'Letzte Änderung rückgängig gemacht.'
}

useSpeechCommand({ id: 'review', label: 'Text prüfen', phrases: ['prüfen', 'text prüfen'], enabled: () => !props.disabled && !props.inactive && !reviewOpen.value, handler: review })
useSpeechCommand({ id: 'accept-correction', label: 'Übernehmen', phrases: ['übernehmen'], enabled: () => Boolean(current.value?.replacement) && !props.disabled && !actionLocked.value, handler: apply })
useSpeechCommand({ id: 'keep-correction', label: 'Behalten', phrases: ['behalten'], enabled: () => Boolean(current.value) && !props.disabled && !actionLocked.value, handler: keep })
useSpeechCommand({ id: 'undo-correction', label: 'Rückgängig', phrases: ['rückgängig'], enabled: () => Boolean(undo.value) && !props.disabled && !props.inactive, handler: restore })
function closeReview() {
  reviewOpen.value = false
  status.value = issues.value.length ? `${issues.value.length} Stellen noch zu prüfen. Sage „Text prüfen“.` : 'Prüfung beendet. Fehler können trotzdem vorkommen.'
}
useSpeechCommand({ id: 'close-review', label: 'Prüfung schließen', phrases: ['prüfung schließen'], enabled: () => reviewOpen.value, handler: closeReview })
useSpeechCommand({ id: 'edit-text', label: 'Text bearbeiten', phrases: ['text bearbeiten'], enabled: () => !props.disabled && !props.inactive && !reviewOpen.value, handler: edit })
onBeforeUnmount(() => {
  request?.abort()
  emit('active', false)
})
</script>

<template>
  <section
    class="space-y-3 rounded-3xl border border-default p-4 sm:space-y-4 sm:p-5"
    aria-label="Text prüfen und korrigieren"
  >
    <h2 class="text-lg font-semibold text-muted">
      Dein Text
    </h2>
    <p
      v-if="!editing"
      tabindex="0"
      class="min-h-24 max-h-[30dvh] overflow-y-auto whitespace-pre-wrap break-words text-xl font-semibold leading-relaxed"
    >
      <template
        v-for="(part, index) in parts"
        :key="index"
      >
        <mark
          v-if="part.number"
          class="bg-warning/15 text-highlighted underline decoration-2 underline-offset-4"
        >{{ part.text }}<sup class="ml-1">{{ part.number }}</sup></mark><template v-else>
          {{ part.text }}
        </template>
      </template>
    </p>
    <UTextarea
      v-else
      :model-value="text"
      aria-label="Erkannter Freitext"
      autofocus
      autoresize
      class="w-full"
      :readonly="disabled || reviewOpen"
      :rows="7"
      size="xl"
      :ui="{ base: 'min-h-56 rounded-2xl p-5 text-xl font-semibold leading-relaxed' }"
      @update:model-value="emit('updateText', $event)"
    />
    <p
      role="status"
      aria-live="polite"
      class="min-h-12 text-base text-toned"
    >
      {{ status }}
    </p>

    <div
      v-if="!reviewOpen"
      class="grid grid-cols-2 gap-4"
    >
      <UButton
        block
        class="min-h-20"
        size="xl"
        type="button"
        :disabled="disabled || checking || !text.trim()"
        variant="soft"
        @click="review"
      >
        Text prüfen
      </UButton>
      <UButton
        aria-label="Rückgängig"
        block
        class="min-h-20"
        size="xl"
        icon="i-lucide-rotate-ccw"
        type="button"
        color="neutral"
        variant="outline"
        :disabled="disabled || !undo"
        @click="restore"
      />
      <UButton
        block
        class="col-span-2 min-h-20"
        size="xl"
        type="button"
        color="neutral"
        variant="outline"
        icon="i-lucide-pencil"
        :disabled="disabled"
        @click="edit"
      >
        Text bearbeiten
      </UButton>
    </div>
    <UModal
      :open="reviewOpen"
      title="Text prüfen"
      description="Übernimm den Vorschlag oder behalte deinen Text."
      :close="false"
      :dismissible="false"
      :ui="{ content: 'rounded-3xl', title: 'text-2xl', description: 'text-lg', footer: 'p-4 sm:p-6' }"
    >
      <template #body>
        <div class="min-h-48 space-y-5 text-xl leading-relaxed">
          <p
            role="status"
            aria-live="polite"
            class="font-semibold text-highlighted"
          >
            {{ current ? `Stelle ${current.number} von ${reviewTotal}` : 'Prüfung beendet' }}
          </p>
          <template v-if="current">
            <p class="whitespace-pre-wrap">
              {{ context?.before }}<mark class="bg-warning/15 text-highlighted underline decoration-2 underline-offset-4">{{ current.original }}</mark>{{ context?.after }}
            </p>
            <div class="rounded-2xl bg-elevated p-4">
              <p class="text-base text-muted">
                Vorschlag
              </p>
              <p class="font-semibold text-highlighted">
                {{ current.replacement }}
              </p>
            </div>
          </template>
          <p v-else>
            Alle Vorschläge wurden geprüft. Fehler können trotzdem vorkommen.
          </p>
        </div>
      </template>
      <template #footer>
        <div class="grid w-full grid-cols-2 gap-4">
          <UButton
            block
            class="col-span-2 min-h-20"
            size="xl"
            type="button"
            :disabled="!current || disabled || actionLocked"
            @click="apply"
          >
            Übernehmen
          </UButton>
          <UButton
            block
            class="col-span-2 min-h-20"
            size="xl"
            type="button"
            color="neutral"
            variant="soft"
            :disabled="!current || disabled || actionLocked"
            @click="keep"
          >
            Behalten
          </UButton>
          <UButton
            block
            class="min-h-20"
            size="xl"
            type="button"
            color="neutral"
            variant="outline"
            :disabled="!undo || disabled"
            @click="restore"
          >
            Rückgängig
          </UButton>
          <UButton
            block
            class="min-h-20"
            size="xl"
            type="button"
            color="neutral"
            variant="outline"
            @click="closeReview"
          >
            Schließen
          </UButton>
        </div>
      </template>
    </UModal>
  </section>
</template>
