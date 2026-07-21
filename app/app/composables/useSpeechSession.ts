import type { Phrase, Suggestion, TranscriptionResult } from '~/types/speech'

type SpeechMode = 'phrases' | 'math'

export function useSpeechSession(mode: Ref<SpeechMode>) {
  const recorder = shallowRef<MediaRecorder>()
  const chunks = ref<Blob[]>([])
  const result = ref<TranscriptionResult>()
  const selected = ref<Suggestion>()
  const status = ref('')
  const isRecording = ref(false)
  const isBusy = ref(false)
  const isSaving = ref(false)
  const hasSaved = ref(false)
  const recordingDone = shallowRef<Promise<void>>()

  const suggestions = computed(() => result.value?.suggestions ?? [])
  const hasSelection = computed(() => Boolean(selected.value))
  const hasMathResult = computed(() => mode.value === 'math' && Boolean(result.value?.math_text))
  const selectedIndex = computed(() => suggestions.value.findIndex(suggestion => suggestion.phrase_id === selected.value?.phrase_id))
  const outputText = computed(() => mode.value === 'math' ? result.value?.math_text : selected.value?.text)

  const silenceDetection = useSilenceDetection(stopRecording)

  function setSelection(suggestion: Suggestion) {
    selected.value = suggestion
  }

  function selectSuggestionAt(index: number) {
    if (!suggestions.value.length) return
    const nextIndex = (index + suggestions.value.length) % suggestions.value.length
    selected.value = suggestions.value[nextIndex]
    status.value = 'Vorschlag gewechselt.'
  }

  function selectPhrase(phrase: Phrase) {
    result.value = undefined
    selected.value = {
      phrase_id: phrase.id,
      text: phrase.text,
      score: 1
    }
    hasSaved.value = false
    status.value = 'Direkt ausgewählt.'
  }

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    let resolveRecordingDone: () => void = () => {}
    recordingDone.value = new Promise((resolve) => {
      resolveRecordingDone = resolve
    })
    chunks.value = []
    result.value = undefined
    selected.value = undefined
    hasSaved.value = false
    status.value = ''
    recorder.value = new MediaRecorder(stream)
    recorder.value.ondataavailable = event => chunks.value.push(event.data)
    recorder.value.onstop = async () => {
      silenceDetection.stop()
      stream.getTracks().forEach(track => track.stop())
      await transcribe(new Blob(chunks.value, { type: recorder.value?.mimeType || 'audio/webm' }))
      resolveRecordingDone()
    }
    recorder.value.start()
    silenceDetection.start(stream)
    isRecording.value = true
    status.value = 'Aufnahme läuft...'
    await recordingDone.value
  }

  function stopRecording() {
    if (!recorder.value || recorder.value.state === 'inactive') return
    isRecording.value = false
    isBusy.value = true
    status.value = 'Ich höre zu...'
    recorder.value.stop()
  }

  async function transcribe(blob: Blob) {
    const form = new FormData()
    form.append('audio', blob, 'recording.webm')

    try {
      const response = await fetch('/api/transcribe', { method: 'POST', body: form })
      if (!response.ok) throw new Error('Erkennung fehlgeschlagen.')
      result.value = await response.json()
      selected.value = mode.value === 'phrases' ? result.value?.suggestions[0] : undefined
      hasSaved.value = false
      status.value = mode.value === 'math'
        ? 'Mathe erkannt.'
        : selected.value ? 'Meinst du das?' : 'Kein Vorschlag gefunden.'
    } catch (error) {
      status.value = error instanceof Error ? error.message : 'Erkennung fehlgeschlagen.'
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

  async function saveAttempt() {
    const correctedText = outputText.value
    if (!result.value || !correctedText || hasSaved.value || isSaving.value) return
    isSaving.value = true
    const top = result.value.suggestions[0]
    const form = new FormData()
    form.append('audio_id', result.value.audio_id)
    form.append('source', mode.value === 'math' ? 'friend_app_math' : 'friend_app')
    form.append('phrase_id', selected.value ? String(selected.value.phrase_id) : '')
    form.append('expected_text', correctedText)
    form.append('raw_transcript', result.value.raw_transcript)
    form.append('corrected_text', correctedText)
    form.append('suggested_phrase_id', top?.phrase_id ? String(top.phrase_id) : '')
    form.append('suggested_text', top?.text || '')
    form.append('suggestion_score', top?.score ? String(top.score) : '')
    form.append('was_understandable', 'true')
    try {
      await fetch('/api/speech-attempts', { method: 'POST', body: form })
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
    copySelected
  }
}
