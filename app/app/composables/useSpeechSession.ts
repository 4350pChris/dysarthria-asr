import type { Phrase, Suggestion, TranscriptionResult } from '~/types/speech'
import { useDebounceFn } from '@vueuse/core'

type SpeechMode = 'phrases' | 'math' | 'emoji' | 'freetext'

export function useSpeechSession(mode: Ref<SpeechMode>) {
  const { track } = useUsageAnalytics()
  const result = ref<TranscriptionResult>()
  const selected = ref<Suggestion>()
  const freeText = ref('')
  const status = ref('')
  const isBusy = ref(false)
  const isSaving = ref(false)
  const hasSaved = ref(false)
  let partialRequest: AbortController | undefined
  const { isSafeToUpdate } = usePwaUpdateSafety()
  const {
    isRecording,
    start: startAudioRecording,
    stop: stopAudioRecording
  } = useAudioRecording({
    onComplete: transcribe,
    onChunk: transcribePartial,
    onStopping: () => {
      isBusy.value = true
      status.value = 'Ich höre zu...'
    }
  })

  const suggestions = computed(() => result.value?.suggestions ?? [])
  const hasSelection = computed(() => Boolean(selected.value))
  const hasMathResult = computed(
    () => mode.value === 'math' && Boolean(result.value?.math_text)
  )
  const hasEmojiResult = computed(
    () => mode.value === 'emoji' && Boolean(result.value?.emoji_name)
  )
  const selectedIndex = computed(() =>
    suggestions.value.findIndex(
      suggestion => suggestion.id === selected.value?.id
    )
  )
  const outputText = computed(() =>
    mode.value === 'freetext'
      ? freeText.value
      : mode.value === 'math'
        ? result.value?.math_text
        : mode.value === 'emoji'
          ? result.value?.emoji_value
          : selected.value?.text
  )
  const saveFreeText = useDebounceFn(() => {
    void saveAttempt()
  }, 500)

  watch([isRecording, isBusy], ([recording, busy]) => {
    isSafeToUpdate.value = !recording && !busy
  }, { immediate: true })

  onScopeDispose(() => {
    isSafeToUpdate.value = true
  })

  function setSelection(suggestion: Suggestion) {
    selected.value = suggestion
    track('suggestion_selected', { source: suggestion.source })
  }

  function selectSuggestionAt(index: number) {
    if (!suggestions.value.length) return
    const nextIndex
      = (index + suggestions.value.length) % suggestions.value.length
    const suggestion = suggestions.value[nextIndex]
    if (!suggestion) return
    selected.value = suggestion
    track('suggestion_selected', {
      source: suggestion.source
    })
    status.value = 'Vorschlag gewechselt.'
  }

  function selectPhrase(phrase: Phrase) {
    result.value = undefined
    selected.value = {
      id: `phrase:${phrase.id}`,
      source: 'phrase',
      text: phrase.text,
      score: 1
    }
    hasSaved.value = false
    status.value = 'Direkt ausgewählt.'
    track('phrase_selected')
  }

  async function startRecording() {
    result.value = undefined
    selected.value = undefined
    if (mode.value === 'freetext') freeText.value = ''
    hasSaved.value = false
    status.value = ''
    status.value = 'Aufnahme läuft...'
    await startAudioRecording()
    track('recording_started', { mode: mode.value })
  }

  function stopRecording() {
    stopAudioRecording()
  }

  async function transcribe(blob: Blob) {
    partialRequest?.abort()
    const form = new FormData()
    form.append('audio', blob, 'recording.webm')

    try {
      const response = await fetch('/api/transcribe', {
        method: 'POST',
        body: form
      })
      if (!response.ok) {
        const body = await response.json().catch(() => undefined)
        const message = body && typeof body.detail === 'string'
          ? body.detail
          : 'Erkennung fehlgeschlagen.'
        throw new Error(message)
      }
      const transcription: TranscriptionResult = await response.json()
      result.value = transcription
      if (mode.value === 'freetext') {
        freeText.value = transcription.raw_transcript
      }
      selected.value
        = mode.value === 'phrases'
          ? transcription.emoji_text !== transcription.raw_transcript
            ? {
                id: 'emoji:recognized',
                source: 'emoji',
                text: transcription.emoji_text,
                score: 1
              }
            : transcription.suggestions[0]
          : undefined
      hasSaved.value = false
      status.value
        = mode.value === 'math'
          ? 'Mathe erkannt.'
          : mode.value === 'emoji'
            ? transcription.emoji_name
              ? 'Emoji erkannt.'
              : 'Emoji nicht erkannt. Bitte sage den Namen des Emojis.'
            : mode.value === 'freetext'
              ? freeText.value
                ? 'Text erkannt.'
                : 'Kein Text erkannt.'
              : selected.value
                ? 'Meinst du das?'
                : 'Kein Vorschlag gefunden.'
      track('transcription_completed', {
        mode: mode.value,
        outcome: mode.value === 'phrases'
          ? (selected.value ? 'selection_available' : 'no_selection')
          : mode.value === 'math'
            ? (transcription.math_text ? 'result_available' : 'no_result')
            : mode.value === 'emoji'
              ? (transcription.emoji_name ? 'result_available' : 'no_result')
              : (freeText.value ? 'result_available' : 'no_result')
      })
    } catch (error) {
      status.value
        = error instanceof Error ? error.message : 'Erkennung fehlgeschlagen.'
      track('transcription_failed', { mode: mode.value })
    } finally {
      isBusy.value = false
    }
  }

  async function transcribePartial(blob: Blob) {
    if (mode.value !== 'freetext' || partialRequest) return

    const controller = new AbortController()
    partialRequest = controller
    const form = new FormData()
    form.append('audio', blob, 'recording.webm')

    try {
      const response = await fetch('/api/transcribe/partial', {
        method: 'POST',
        body: form,
        signal: controller.signal
      })
      if (!response.ok) return
      const body: unknown = await response.json()
      if (
        body
        && typeof body === 'object'
        && 'raw_transcript' in body
        && typeof body.raw_transcript === 'string'
        && body.raw_transcript
      ) {
        freeText.value = body.raw_transcript
        status.value = 'Text wird erkannt...'
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        // The final transcription reports errors to the user.
      }
    } finally {
      if (partialRequest === controller) partialRequest = undefined
    }
  }

  function speakSelected() {
    if (!outputText.value) return
    speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(outputText.value)
    utterance.lang = 'de-DE'
    speechSynthesis.speak(utterance)
    track('message_spoken', { mode: mode.value })
    void saveAttempt()
  }

  async function copySelected() {
    if (!outputText.value) return
    try {
      await navigator.clipboard.writeText(outputText.value)
      status.value = 'Kopiert.'
      track('message_copied', { mode: mode.value })
      void saveAttempt()
    } catch {
      status.value = 'Kopieren nicht möglich.'
    }
  }

  function setFreeText(text: string) {
    freeText.value = text
    hasSaved.value = false
    if (mode.value === 'freetext') saveFreeText()
  }

  async function shareToInstagram() {
    if (!outputText.value) return
    const image = createShareImage(outputText.value)
    if (!image) {
      status.value = 'Bild konnte nicht erstellt werden.'
      return
    }

    if (!navigator.share || !navigator.canShare?.({ files: [image] })) {
      status.value = 'Instagram-Teilen wird auf diesem Gerät nicht unterstützt.'
      return
    }

    try {
      await navigator.share({
        text: outputText.value,
        files: [image]
      })
      status.value = 'Bild zum Teilen geöffnet.'
      track('message_shared', { channel: 'instagram', mode: mode.value })
    } catch {
      status.value = 'Instagram-Teilen abgebrochen.'
    }
    void saveAttempt()
  }

  async function shareText() {
    if (!outputText.value) return
    try {
      if (navigator.share) {
        await navigator.share({ text: outputText.value })
        status.value = 'Text geteilt.'
        track('message_shared', { channel: 'native_share', mode: mode.value })
      } else {
        if (openWhatsapp(outputText.value)) {
          track('message_shared', { channel: 'whatsapp', mode: mode.value })
        }
      }
    } catch {
      if (openWhatsapp(outputText.value)) {
        track('message_shared', { channel: 'whatsapp', mode: mode.value })
      }
    }
    void saveAttempt()
  }

  function openWhatsapp(text: string) {
    const url = `https://wa.me/?text=${encodeURIComponent(text)}`
    const opened = window.open(url, '_blank', 'noopener,noreferrer')
    status.value = opened
      ? 'WhatsApp geöffnet.'
      : 'WhatsApp konnte nicht geöffnet werden.'
    return Boolean(opened)
  }

  function createShareImage(text: string): File | undefined {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) return undefined

    const padding = 96
    const maxWidth = 900
    const font = 'bold 52px system-ui, sans-serif'
    context.font = font
    const lines = wrapShareText(context, text, maxWidth - padding * 2)
    const lineHeight = 72
    canvas.width = maxWidth
    canvas.height = Math.max(360, padding * 2 + lines.length * lineHeight)

    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.fillStyle = '#18181b'
    context.font = font
    context.textBaseline = 'top'
    lines.forEach((line, index) => {
      context.fillText(line, padding, padding + index * lineHeight)
    })

    const data = canvas.toDataURL('image/png').split(',', 2)[1]
    if (!data) return undefined
    const bytes = Uint8Array.from(atob(data), character => character.charCodeAt(0))
    return new File([bytes], 'sprachhilfe-nachricht.png', { type: 'image/png' })
  }

  function wrapShareText(
    context: CanvasRenderingContext2D,
    text: string,
    maxWidth: number
  ) {
    const lines: string[] = []
    let line = ''

    for (const word of text.split(/\s+/)) {
      const nextLine = line ? `${line} ${word}` : word
      if (line && context.measureText(nextLine).width > maxWidth) {
        lines.push(line)
        line = word
      } else {
        line = nextLine
      }
    }
    if (line) lines.push(line)
    return lines
  }

  async function saveAttempt() {
    const correctedText = mode.value === 'freetext'
      ? freeText.value
      : mode.value === 'emoji'
        ? result.value?.emoji_name
        : outputText.value
    if (!result.value || !correctedText || hasSaved.value || isSaving.value)
      return
    isSaving.value = true
    try {
      await fetch(`/api/labeling/items/${result.value.audio_id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          notes: mode.value === 'freetext'
            ? 'Edited free text.'
            : 'Provisional app selection.',
          status: 'draft',
          transcript: correctedText,
          unsure: false
        }),
        headers: { 'Content-Type': 'application/json' }
      })
      hasSaved.value = true
    } finally {
      isSaving.value = false
    }
  }

  return {
    result,
    selected,
    freeText,
    status,
    isRecording,
    isBusy,
    suggestions,
    hasSelection,
    hasMathResult,
    hasEmojiResult,
    selectedIndex,
    outputText,
    setSelection,
    setFreeText,
    selectSuggestionAt,
    selectPhrase,
    startRecording,
    stopRecording,
    speakSelected,
    copySelected,
    shareToInstagram,
    shareText
  }
}
