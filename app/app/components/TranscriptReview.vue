<script setup lang="ts">
type Issue = { original: string, replacement: string, start: number, number: number }

const props = defineProps<{ text: string, audioId?: string, disabled?: boolean }>()
const emit = defineEmits<{ updateText: [text: string], active: [active: boolean], busy: [busy: boolean] }>()
const commands = useSpeechCommands()
const issues = ref<Issue[]>([])
const current = ref<Issue>()
const checking = ref(false)
const selectingSentence = ref(false)
const editing = ref(false)
const busy = ref(false)
const status = ref('')
const undo = ref<{ before: string, after: string }>()
const audio = ref<HTMLAudioElement>()
const reviewPanel = ref<HTMLElement>()
let snapshot = props.text
let expectedText: string | undefined
let request: AbortController | undefined
let releaseRecording: (() => void) | undefined
let releasePlayback: (() => void) | undefined
let disposed = false

function resumePlaybackCommands() {
  releasePlayback?.()
  releasePlayback = undefined
}

const recording = useAudioRecording({
  onComplete: recognizeReplacement,
  autoStopOnSilence: useLocalStorage('auto-stop-on-silence', true),
  withAudioLevel: true
})
watch(busy, value => emit('busy', value), { flush: 'sync' })
const active = computed(() => Boolean(current.value) || selectingSentence.value || busy.value)
watch(active, value => emit('active', value), { flush: 'sync' })
watch(current, async (issue) => {
  if (!issue) return
  await nextTick()
  reviewPanel.value?.focus()
})

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
// ponytail: punctuation splits sentences; use a German segmenter if abbreviations cause trouble.
const sentences = computed(() => [...props.text.matchAll(/[^.!?\n]+(?:[.!?]+|$)/g)]
  .filter(match => match[0].trim())
  .map((match, index) => ({ original: match[0].trim(), replacement: '', start: match.index + match[0].indexOf(match[0].trim()), number: index + 1 })))

watch(() => [props.text, props.audioId, props.disabled] as const, ([text, audioId, disabled], previous) => {
  if (text === expectedText && audioId === previous?.[1] && !disabled) {
    snapshot = text
    expectedText = undefined
    return
  }
  request?.abort()
  audio.value?.pause()
  resumePlaybackCommands()
  snapshot = text
  expectedText = undefined
  issues.value = []
  current.value = undefined
  selectingSentence.value = false
  editing.value = false
  undo.value = undefined
  status.value = ''
  checking.value = false
  if (audioId && !disabled && (audioId !== previous?.[1] || previous?.[2])) void check()
}, { immediate: true })

async function check() {
  if (props.disabled || busy.value || checking.value || !props.audioId) return
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
    if (!controller.signal.aborted) status.value = 'Textprüfung nicht verfügbar. Mit „Satz korrigieren“ kannst du selbst eine Stelle ändern.'
  } finally {
    if (request === controller) checking.value = false
  }
}

function review() {
  if (props.disabled || busy.value) return
  if (issues.value.length) {
    current.value = issues.value[0]
    status.value = 'Sage „Übernehmen“, „Behalten“ oder „Neu sprechen“.'
  } else void check()
}

function keep() {
  if (!current.value || busy.value) return
  issues.value = issues.value.filter(issue => issue !== current.value)
  current.value = issues.value[0]
  status.value = 'Original behalten.'
}

function apply() {
  const issue = current.value
  if (!issue?.replacement || busy.value || props.disabled) return
  if (props.text !== snapshot || props.text.slice(issue.start, issue.start + issue.original.length) !== issue.original) return
  const text = props.text.slice(0, issue.start) + issue.replacement + props.text.slice(issue.start + issue.original.length)
  undo.value = { before: props.text, after: text }
  issues.value = issues.value.filter(item => item.start + item.original.length <= issue.start || item.start >= issue.start + issue.original.length).map(item => ({
    ...item, start: item.start > issue.start ? item.start + issue.replacement.length - issue.original.length : item.start
  }))
  current.value = issues.value[0]
  expectedText = text
  emit('updateText', text)
  status.value = 'Änderung übernommen.'
}

function restore() {
  if (!undo.value || props.text !== undo.value.after || busy.value || props.disabled) return
  const text = undo.value.before
  issues.value = []
  current.value = undefined
  expectedText = text
  undo.value = undefined
  emit('updateText', text)
  status.value = 'Letzte Änderung rückgängig gemacht.'
}

async function recordReplacement() {
  if (!current.value || busy.value || props.disabled) return
  audio.value?.pause()
  resumePlaybackCommands()
  commands.speak('')
  current.value.replacement = ''
  busy.value = true
  releaseRecording = commands.pause()
  status.value = 'Sag den richtigen Ausdruck. Tippe auf „Stopp“, wenn du fertig bist.'
  try {
    await recording.start()
  } catch {
    status.value = 'Aufnahme nicht möglich. Der Text bleibt unverändert.'
  } finally {
    busy.value = false
    releaseRecording?.()
    releaseRecording = undefined
  }
}

async function recognizeReplacement(blob: Blob) {
  if (disposed) return
  const issue = current.value
  const text = props.text
  status.value = 'Dein Ausdruck wird erkannt …'
  const form = new FormData()
  form.append('audio', blob, 'replacement.webm')
  try {
    const result = await $fetch<{ text: string }>('/api/transcribe/replacement', { method: 'POST', body: form })
    if (disposed || current.value !== issue || props.text !== text || !issue) return
    issue.replacement = result.text
    status.value = 'Vorschlag erkannt. Sage „Übernehmen“ oder „Neu sprechen“.'
  } catch {
    if (!disposed) status.value = 'Nicht verstanden. Der Text bleibt unverändert. Du kannst es erneut versuchen.'
  }
}

const correctionActions = [
  { label: 'Übernehmen', handler: apply, color: 'primary', variant: 'solid' },
  { label: 'Behalten', handler: keep, color: 'neutral', variant: 'soft' },
  { label: 'Neu sprechen', handler: recordReplacement, color: 'neutral', variant: 'soft' }
] as const

function manual() {
  if (props.disabled || busy.value) return
  current.value = undefined
  selectingSentence.value = true
  status.value = 'Wähle einen Satz oder sage „Satz eins“, „Satz zwei“ und so weiter.'
}

function selectSentence(issue: Issue) {
  selectingSentence.value = false
  current.value = { ...issue }
  status.value = 'Sage „Neu sprechen“, um diesen Satz zu ersetzen.'
}

async function play() {
  if (!audio.value || busy.value) return
  commands.speak('')
  resumePlaybackCommands()
  releasePlayback = commands.pause()
  try {
    audio.value.currentTime = 0
    await audio.value.play()
  } catch {
    resumePlaybackCommands()
    status.value = 'Die Aufnahme konnte nicht abgespielt werden.'
  }
}

useSpeechCommand({ id: 'review', label: 'Prüfen', phrases: ['prüfen', 'text prüfen'], enabled: () => !props.disabled && !active.value, handler: review })
useSpeechCommand({ id: 'correct-sentence', label: 'Satz korrigieren', phrases: ['satz korrigieren'], enabled: () => !props.disabled && !active.value, handler: manual })
useSpeechCommand({ id: 'accept-correction', label: 'Übernehmen', phrases: ['übernehmen'], enabled: () => Boolean(current.value?.replacement) && !busy.value && !props.disabled, handler: apply })
useSpeechCommand({ id: 'keep-correction', label: 'Behalten', phrases: ['behalten'], enabled: () => Boolean(current.value) && !busy.value && !props.disabled, handler: keep })
useSpeechCommand({ id: 'record-correction', label: 'Neu sprechen', phrases: ['neu sprechen'], enabled: () => Boolean(current.value) && !busy.value && !props.disabled, handler: recordReplacement })
useSpeechCommand({ id: 'undo-correction', label: 'Rückgängig', phrases: ['rückgängig'], enabled: () => Boolean(undo.value) && !busy.value && !props.disabled, handler: restore })
useSpeechCommand({ id: 'play-recording', label: 'Anhören', phrases: ['anhören'], enabled: () => Boolean(props.audioId) && !busy.value && !props.disabled, handler: play })
function readSuggestion() {
  if (!current.value || busy.value) return
  commands.speak(`Erkannt: ${current.value.original}. ${current.value.replacement ? `Vorschlag: ${current.value.replacement}` : 'Sage „Neu sprechen“, um den Satz zu ersetzen.'}`)
}
useSpeechCommand({ id: 'read-suggestion', label: 'Vorlesen', phrases: ['vorlesen'], enabled: () => Boolean(current.value) && !busy.value && !props.disabled, handler: readSuggestion })
function closeReview() {
  if (busy.value) return
  current.value = undefined
  selectingSentence.value = false
}
useSpeechCommand({ id: 'close-review', label: 'Prüfung schließen', phrases: ['prüfung schließen'], enabled: () => active.value && !busy.value, handler: closeReview })
const numberNames = ['eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn']
watch(sentences, (items, _, onCleanup) => {
  const unregister = items.map(issue => commands.register({
    id: `correct-sentence-${issue.number}`, label: `Satz ${issue.number}`,
    phrases: [`satz ${issue.number}`, `satz ${numberNames[issue.number - 1] || issue.number}`],
    enabled: () => selectingSentence.value && !props.disabled,
    handler: () => selectSentence(issue)
  }))
  onCleanup(() => unregister.forEach(remove => remove()))
}, { immediate: true })

onBeforeUnmount(() => {
  disposed = true
  request?.abort()
  audio.value?.pause()
  resumePlaybackCommands()
  releaseRecording?.()
  emit('active', false)
  emit('busy', false)
})
</script>

<template>
  <section
    class="space-y-4"
    aria-label="Text prüfen und korrigieren"
  >
    <p
      v-if="issues.length && !editing"
      class="min-h-56 whitespace-pre-wrap rounded-2xl border border-default p-5 text-xl font-semibold leading-relaxed"
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
      autoresize
      class="w-full"
      :readonly="disabled || busy"
      :rows="7"
      size="xl"
      :ui="{ base: 'min-h-56 rounded-2xl p-5 text-xl font-semibold leading-relaxed' }"
      @update:model-value="emit('updateText', $event)"
    />
    <p
      role="status"
      aria-live="polite"
      class="text-lg text-toned"
    >
      {{ status }}
    </p>

    <template v-if="!active">
      <UButton
        block
        class="min-h-20"
        size="xl"
        type="button"
        :disabled="disabled || checking || !audioId"
        variant="soft"
        @click="review"
      >
        Prüfen
      </UButton>
      <UButton
        block
        class="min-h-20"
        size="xl"
        type="button"
        color="neutral"
        variant="soft"
        :disabled="disabled"
        @click="manual"
      >
        Satz korrigieren
      </UButton>
      <UButton
        v-if="issues.length"
        block
        class="min-h-20"
        size="xl"
        type="button"
        color="neutral"
        variant="outline"
        :disabled="disabled"
        @click="editing = !editing"
      >
        {{ editing ? 'Markierungen anzeigen' : 'Text bearbeiten' }}
      </UButton>
    </template>

    <div
      v-if="selectingSentence"
      class="space-y-3"
    >
      <UButton
        v-for="sentence in sentences"
        :key="sentence.number"
        block
        class="min-h-20 whitespace-normal text-left"
        size="xl"
        type="button"
        variant="soft"
        :disabled="disabled"
        @click="selectSentence(sentence)"
      >
        Satz {{ sentence.number }}: {{ sentence.original }}
      </UButton>
    </div>

    <div
      v-if="current"
      ref="reviewPanel"
      tabindex="-1"
      aria-label="Ausgewählte Stelle prüfen"
      class="space-y-4 rounded-2xl border border-default p-5"
    >
      <p class="text-lg font-semibold">
        Bitte prüfen · Stelle {{ current.number }}
      </p>
      <p class="whitespace-pre-wrap text-xl">
        {{ current.original }}
      </p>
      <p
        v-if="current.replacement"
        class="text-xl font-semibold"
      >
        Meintest du: {{ current.replacement }}?
      </p>
      <UButton
        block
        class="min-h-20"
        size="xl"
        type="button"
        color="neutral"
        variant="soft"
        :disabled="disabled || busy"
        @click="readSuggestion"
      >
        Vorlesen
      </UButton>
      <div class="space-y-3">
        <UButton
          v-for="action in correctionActions"
          :key="action.label"
          block
          class="min-h-20"
          size="xl"
          type="button"
          :color="action.color"
          :variant="action.variant"
          :disabled="disabled || busy || (action.handler === apply && !current.replacement)"
          @click="action.handler"
        >
          {{ action.label }}
        </UButton>
      </div>
    </div>
    <UButton
      v-if="recording.isRecording.value"
      block
      class="min-h-24"
      size="xl"
      type="button"
      color="warning"
      @click="recording.stop"
    >
      Stopp
    </UButton>
    <AudioLevelMeter
      v-if="recording.isRecording.value"
      :level="recording.audioLevel.value"
    />
    <UButton
      v-if="active"
      block
      class="min-h-20"
      size="xl"
      type="button"
      color="neutral"
      variant="outline"
      :disabled="busy"
      @click="closeReview"
    >
      Prüfung schließen
    </UButton>
    <UButton
      v-if="undo"
      block
      class="min-h-20"
      size="xl"
      type="button"
      color="neutral"
      variant="outline"
      :disabled="disabled || busy"
      @click="restore"
    >
      Rückgängig
    </UButton>
    <template v-if="audioId">
      <UButton
        block
        class="min-h-20"
        size="xl"
        type="button"
        color="neutral"
        variant="soft"
        :disabled="disabled || busy"
        @click="play"
      >
        Anhören
      </UButton>
      <audio
        v-show="!busy"
        ref="audio"
        class="w-full"
        controls
        preload="none"
        :src="`/api/labeling/audio/${audioId}`"
        @play="commands.speak(''); releasePlayback ||= commands.pause()"
        @pause="resumePlaybackCommands"
        @ended="resumePlaybackCommands"
        @error="resumePlaybackCommands"
      />
    </template>
  </section>
</template>
