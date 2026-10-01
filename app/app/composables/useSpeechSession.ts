import type { TranscriptionResult } from '~/types/speech'
import { useDebounceFn } from '@vueuse/core'
import { enqueueRecording } from '~/utils/recordingUploadQueue'

type SpeechMode = 'text' | 'math' | 'emoji'
type SelectedEmoji = { name: string, value: string }

export function useSpeechSession(mode: Ref<SpeechMode>, autoStopOnSilence: Ref<boolean>, correctionBusy = ref(false)) {
  const speechCommands = useSpeechCommands()
  const { track } = useUsageAnalytics()
  const backendAvailable = useBackendAvailability()
  const offline = useOfflineTranscription()
  onMounted(() => {
    void offline.prepare()
  })
  const result = ref<TranscriptionResult>()
  const selectedEmoji = ref<SelectedEmoji>()
  const emojiHistory = useLocalStorage<SelectedEmoji[]>('emoji-history', [])
  const freeText = ref('')
  const status = ref('')
  const isBusy = ref(false)
  const isSaving = ref(false)
  const hasSaved = ref(false)
  const { start: startLiveTranscription, stop: stopLiveTranscription } = useLiveTranscription({
    onText(text) {
      if (mode.value !== 'text' || !text) return
      freeText.value = text
      status.value = 'Text wird erkannt...'
    }
  })
  const { isSafeToUpdate } = usePwaUpdateSafety()
  const {
    audioLevel,
    isRecording,
    start: startAudioRecording,
    stop: stopAudioRecording
  } = useAudioRecording({
    onComplete: transcribe,
    autoStopOnSilence,
    withAudioLevel: true,
    onStream: (stream) => {
      if (mode.value === 'text' && backendAvailable.value) void startLiveTranscription(stream)
    },
    onStopping: () => {
      stopLiveTranscription()
      isBusy.value = true
      status.value = 'Ich höre zu...'
    }
  })

  const hasMathResult = computed(
    () => mode.value === 'math' && Boolean(result.value?.math_text)
  )
  const emojiText = computed(() => selectedEmoji.value?.value || result.value?.emoji_value || '')
  const emojiName = computed(() => selectedEmoji.value?.name || result.value?.emoji_name || '')
  const hasEmojiResult = computed(() => mode.value === 'emoji' && Boolean(emojiText.value))
  const outputText = computed(() =>
    mode.value === 'text'
      ? freeText.value
      : mode.value === 'math'
        ? result.value?.math_text
        : mode.value === 'emoji'
          ? emojiText.value
          : undefined
  )
  const labelText = computed(() => mode.value === 'emoji' ? emojiName.value : outputText.value)
  const saveFreeText = useDebounceFn(() => {
    void saveAttempt()
  }, 500)

  watch([isRecording, isBusy, correctionBusy], ([recording, busy, correcting]) => {
    isSafeToUpdate.value = !recording && !busy && !correcting
  }, { immediate: true })

  onScopeDispose(() => {
    isSafeToUpdate.value = true
  })

  async function startRecording() {
    result.value = undefined
    selectedEmoji.value = undefined
    freeText.value = ''
    hasSaved.value = false
    status.value = 'Aufnahme läuft...'
    await startAudioRecording()
    track('recording_started', { mode: mode.value })
  }

  function stopRecording() {
    stopAudioRecording()
  }

  async function transcribe(blob: Blob) {
    try {
      const available = backendAvailable.value
      if (!available) {
        await enqueueRecording(blob)
      }
      if (!available && mode.value !== 'text') {
        throw new Error('Mathe- und Emoji-Erkennung benötigen eine Verbindung zum Server.')
      }
      const transcription = mode.value === 'text' && !available
        ? offlineResult(await offline.transcribe(blob))
        : await transcribeOnline(blob)
      result.value = transcription
      if (mode.value === 'emoji' && transcription.emoji_value && transcription.emoji_name) {
        rememberEmoji({ name: transcription.emoji_name, value: transcription.emoji_value })
      }
      if (mode.value === 'text') {
        freeText.value = transcription.emoji_text
      }
      hasSaved.value = false
      status.value
        = mode.value === 'math'
          ? 'Mathe erkannt.'
          : mode.value === 'emoji'
            ? transcription.emoji_name
              ? 'Emoji erkannt.'
              : 'Emoji nicht erkannt. Bitte sage den Namen des Emojis.'
            : 'Text erkannt.'
      track('transcription_completed', {
        mode: mode.value,
        outcome: mode.value === 'text'
          ? 'text_recognized'
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

  function speakSelected() {
    if (!outputText.value || correctionBusy.value) return
    speechCommands.speak(outputText.value)
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
    saveFreeText()
  }

  function selectEmoji(emoji: SelectedEmoji) {
    result.value = undefined
    selectedEmoji.value = emoji
    rememberEmoji(emoji)
    hasSaved.value = false
    status.value = 'Emoji ausgewählt.'
  }

  function rememberEmoji(emoji: SelectedEmoji) {
    emojiHistory.value = [emoji, ...emojiHistory.value.filter(item => item.value !== emoji.value)].slice(0, 8)
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
    const correctedText = labelText.value
    if (!result.value?.audio_id || !correctedText || hasSaved.value || isSaving.value)
      return
    const audioId = result.value.audio_id
    isSaving.value = true
    try {
      const response = await fetch(`/api/labeling/items/${audioId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          notes: mode.value === 'text' ? 'Edited free text.' : 'Provisional app selection.',
          status: 'draft',
          transcript: correctedText,
          unsure: false
        }),
        headers: { 'Content-Type': 'application/json' }
      })
      if (!response.ok) throw new Error('Speichern fehlgeschlagen.')
      hasSaved.value = result.value?.audio_id === audioId && labelText.value === correctedText
      if (hasSaved.value && status.value.startsWith('Änderung noch nicht gespeichert.')) status.value = 'Änderung gespeichert.'
    } catch {
      status.value = 'Änderung noch nicht gespeichert. Kopieren oder Teilen versucht es erneut.'
    } finally {
      isSaving.value = false
      if (result.value?.audio_id === audioId && labelText.value !== correctedText) saveFreeText()
    }
  }

  return {
    result,
    audioLevel,
    freeText,
    status,
    isRecording,
    isBusy,
    hasMathResult,
    hasEmojiResult,
    emojiName,
    emojiText,
    emojiHistory,
    outputText,
    setFreeText,
    selectEmoji,
    startRecording,
    stopRecording,
    speakSelected,
    copySelected,
    shareToInstagram,
    shareText
  }
}

async function transcribeOnline(blob: Blob): Promise<TranscriptionResult> {
  const form = new FormData()
  form.append('audio', blob, 'recording.webm')
  const response = await fetch('/api/transcribe', { method: 'POST', body: form })
  if (!response.ok) {
    const body = await response.json().catch(() => undefined)
    const message = body && typeof body.detail === 'string'
      ? body.detail
      : 'Erkennung fehlgeschlagen.'
    throw new Error(message)
  }
  return response.json()
}

function offlineResult(rawTranscript: string): TranscriptionResult {
  return {
    audio_id: '',
    audio_path: '',
    raw_transcript: rawTranscript,
    emoji_text: rawTranscript,
    emoji_value: '',
    emoji_name: '',
    math_corrected_text: '',
    math_number_text: '',
    math_text: ''
  }
}
