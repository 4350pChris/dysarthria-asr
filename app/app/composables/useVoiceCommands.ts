type VoiceCommand = 'start' | 'stop' | 'speak' | 'copy' | 'phrasesMode' | 'mathMode' | 'next' | 'previous' | 'help'

type SpeechRecognitionEvent = Event & {
  results: SpeechRecognitionResultList
}

type SpeechRecognitionErrorEvent = Event & {
  error: string
}

type SpeechRecognitionConstructor = new () => SpeechRecognition

type SpeechRecognition = EventTarget & {
  continuous: boolean
  interimResults: boolean
  lang: string
  onend: (() => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  start: () => void
  stop: () => void
}

type WindowWithSpeechRecognition = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor
  webkitSpeechRecognition?: SpeechRecognitionConstructor
}

const COMMANDS: Record<VoiceCommand, string[]> = {
  start: ['aufnehmen', 'aufnahme', 'start', 'los'],
  stop: ['stopp', 'stop', 'anhalten', 'fertig'],
  speak: ['vorlesen', 'sagen', 'sprich', 'sprechen'],
  copy: ['kopieren', 'kopie', 'abschreiben'],
  phrasesMode: ['sätze', 'satzmodus', 'sätze modus'],
  mathMode: ['mathe', 'mathemodus', 'mathe modus'],
  next: ['weiter', 'nächster', 'nächste', 'nein'],
  previous: ['zurück', 'vorheriger', 'vorherige'],
  help: ['hilfe', 'befehle']
}

const COMMAND_LABELS: Record<VoiceCommand, string> = {
  start: 'Aufnehmen',
  stop: 'Stopp',
  speak: 'Vorlesen',
  copy: 'Kopieren',
  phrasesMode: 'Sätze',
  mathMode: 'Mathe',
  next: 'Weiter',
  previous: 'Zurück',
  help: 'Hilfe'
}

function normalizeCommand(text: string) {
  return text
    .toLocaleLowerCase('de-DE')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/[^\p{Letter}\p{Number}\s]/gu, '')
    .trim()
}

function similarity(left: string, right: string) {
  const a = normalizeCommand(left)
  const b = normalizeCommand(right)
  if (!a || !b) return 0

  const rows = Array.from({ length: a.length + 1 }, (_, index) => index)
  for (let i = 1; i <= b.length; i += 1) {
    let previous = rows[0] ?? 0
    rows[0] = i
    for (let j = 1; j <= a.length; j += 1) {
      const current = rows[j] ?? 0
      rows[j] = Math.min(
        current + 1,
        (rows[j - 1] ?? 0) + 1,
        previous + (a.at(j - 1) === b.at(i - 1) ? 0 : 1)
      )
      previous = current
    }
  }

  return 1 - (rows[a.length] ?? 0) / Math.max(a.length, b.length)
}

function matchCommand(text: string) {
  let best: { command: VoiceCommand, score: number } | undefined

  for (const [command, phrases] of Object.entries(COMMANDS) as [VoiceCommand, string[]][]) {
    for (const phrase of phrases) {
      const score = similarity(text, phrase)
      if (!best || score > best.score) {
        best = { command, score }
      }
    }
  }

  return best && best.score >= 0.72 ? best : undefined
}

export function useVoiceCommands(onCommand: (command: VoiceCommand, transcript: string) => void) {
  const isSupported = ref(false)
  const isListening = ref(false)
  const transcript = ref('')
  const status = ref('')
  const recognition = shallowRef<SpeechRecognition>()

  function start() {
    const SpeechRecognition = (window as WindowWithSpeechRecognition).SpeechRecognition
      || (window as WindowWithSpeechRecognition).webkitSpeechRecognition

    if (!SpeechRecognition) {
      status.value = 'Sprachsteuerung wird von diesem Browser nicht unterstützt.'
      return
    }

    recognition.value = new SpeechRecognition()
    recognition.value.continuous = true
    recognition.value.interimResults = false
    recognition.value.lang = 'de-DE'
    recognition.value.onresult = (event) => {
      const result = event.results[event.results.length - 1]
      if (!result) return
      transcript.value = result[0]?.transcript.trim() || ''
      const match = matchCommand(transcript.value)
      if (!match) {
        status.value = `Nicht verstanden: ${transcript.value}`
        return
      }
      status.value = `Erkannt: ${COMMAND_LABELS[match.command]}`
      onCommand(match.command, transcript.value)
    }
    recognition.value.onerror = (event) => {
      status.value = `Sprachsteuerung: ${event.error}`
    }
    recognition.value.onend = () => {
      if (isListening.value) {
        recognition.value?.start()
      }
    }
    recognition.value.start()
    isListening.value = true
    status.value = 'Sprachsteuerung aktiv.'
  }

  function stop() {
    isListening.value = false
    recognition.value?.stop()
    status.value = 'Sprachsteuerung aus.'
  }

  onMounted(() => {
    const speechWindow = window as WindowWithSpeechRecognition
    isSupported.value = Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition)
  })

  onBeforeUnmount(stop)

  return {
    isSupported,
    isListening,
    status,
    transcript,
    start,
    stop
  }
}
