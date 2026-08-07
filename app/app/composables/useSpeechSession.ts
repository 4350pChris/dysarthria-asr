import type { Phrase, Suggestion, TranscriptionResult } from '~/types/speech'

type SpeechMode = 'phrases' | 'math'

export function useSpeechSession(mode: Ref<SpeechMode>) {
  const result = ref<TranscriptionResult>()
  const selected = ref<Suggestion>()
  const status = ref('')
  const isBusy = ref(false)
  const isSaving = ref(false)
  const hasSaved = ref(false)
  const { isSafeToUpdate } = usePwaUpdateSafety()
  const {
    isRecording,
    start: startAudioRecording,
    stop: stopAudioRecording
  } = useAudioRecording({
    onComplete: transcribe,
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
  const selectedIndex = computed(() =>
    suggestions.value.findIndex(
      suggestion => suggestion.id === selected.value?.id
    )
  )
  const outputText = computed(() =>
    mode.value === 'math' ? result.value?.math_text : selected.value?.text
  )

  watch([isRecording, isBusy], ([recording, busy]) => {
    isSafeToUpdate.value = !recording && !busy
  }, { immediate: true })

  onScopeDispose(() => {
    isSafeToUpdate.value = true
  })

  function setSelection(suggestion: Suggestion) {
    selected.value = suggestion
  }

  function selectSuggestionAt(index: number) {
    if (!suggestions.value.length) return
    const nextIndex
      = (index + suggestions.value.length) % suggestions.value.length
    selected.value = suggestions.value[nextIndex]
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
  }

  async function startRecording() {
    result.value = undefined
    selected.value = undefined
    hasSaved.value = false
    status.value = ''
    status.value = 'Aufnahme läuft...'
    await startAudioRecording()
  }

  function stopRecording() {
    stopAudioRecording()
  }

  async function transcribe(blob: Blob) {
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
          : selected.value
            ? 'Meinst du das?'
            : 'Kein Vorschlag gefunden.'
    } catch (error) {
      status.value
        = error instanceof Error ? error.message : 'Erkennung fehlgeschlagen.'
    } finally {
      isBusy.value = false
    }
  }

  function speakSelected() {
    if (!outputText.value) return
    speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(outputText.value)
    utterance.lang = 'de-DE'
    speechSynthesis.speak(utterance)
    void saveAttempt()
  }

  async function copySelected() {
    if (!outputText.value) return
    try {
      await navigator.clipboard.writeText(outputText.value)
      status.value = 'Kopiert.'
      void saveAttempt()
    } catch {
      status.value = 'Kopieren nicht möglich.'
    }
  }

  async function shareSelected() {
    if (!outputText.value) return
    try {
      if (navigator.share) {
        const image = createShareImage(outputText.value)
        const shareData = image && navigator.canShare?.({ files: [image] })
          ? { text: outputText.value, files: [image] }
          : { text: outputText.value }
        await navigator.share(shareData)
        status.value = 'Geteilt.'
      } else {
        openWhatsapp(outputText.value)
      }
    } catch {
      openWhatsapp(outputText.value)
    }
    void saveAttempt()
  }

  function openWhatsapp(text: string) {
    const url = `https://wa.me/?text=${encodeURIComponent(text)}`
    const opened = window.open(url, '_blank', 'noopener,noreferrer')
    status.value = opened
      ? 'WhatsApp geöffnet.'
      : 'WhatsApp konnte nicht geöffnet werden.'
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
    const correctedText = outputText.value
    if (!result.value || !correctedText || hasSaved.value || isSaving.value)
      return
    isSaving.value = true
    try {
      await fetch(`/api/labeling/items/${result.value.audio_id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          notes: 'Provisional app selection.',
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
    status,
    isRecording,
    isBusy,
    suggestions,
    hasSelection,
    hasMathResult,
    selectedIndex,
    outputText,
    setSelection,
    selectSuggestionAt,
    selectPhrase,
    startRecording,
    stopRecording,
    speakSelected,
    copySelected,
    shareSelected
  }
}
