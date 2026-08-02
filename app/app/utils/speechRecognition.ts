export type SpeechRecognitionEvent = Event & {
  resultIndex: number
  results: SpeechRecognitionResultList
}

export type SpeechRecognitionErrorEvent = Event & {
  error: string
}

export type SpeechRecognition = EventTarget & {
  continuous: boolean
  interimResults: boolean
  lang: string
  onend: (() => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionConstructor = new () => SpeechRecognition

type WindowWithSpeechRecognition = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor
  webkitSpeechRecognition?: SpeechRecognitionConstructor
}

function recognitionConstructor() {
  if (typeof window === 'undefined') return undefined
  const speechWindow = window as WindowWithSpeechRecognition
  return speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition
}

export function supportsSpeechRecognition() {
  return Boolean(recognitionConstructor())
}

export function createSpeechRecognition(continuous: boolean) {
  const SpeechRecognition = recognitionConstructor()
  if (!SpeechRecognition) return undefined

  const recognition = new SpeechRecognition()
  recognition.continuous = continuous
  recognition.interimResults = false
  recognition.lang = 'de-DE'
  return recognition
}
