import {
  createSpeechRecognition,
  supportsSpeechRecognition,
  type SpeechRecognition
} from '../utils/speechRecognition'

type SpeechCommand = {
  id: string
  label: string
  phrases: string[]
  handler: () => void | Promise<void>
}

type SpeechCommands = {
  commands: Ref<SpeechCommand[]>
  isListening: Ref<boolean>
  isSupported: Ref<boolean>
  status: Ref<string>
  start: () => void
  stop: () => void
  register: (command: SpeechCommand) => () => void
}

const speechCommandsKey = Symbol('speech-commands')

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

export function createSpeechCommands(): SpeechCommands {
  const commands = ref<SpeechCommand[]>([])
  const isSupported = ref(false)
  const isListening = ref(false)
  const status = ref('')
  const recognition = shallowRef<SpeechRecognition>()

  function register(command: SpeechCommand) {
    commands.value = [...commands.value, command]
    return () => {
      commands.value = commands.value.filter(item => item !== command)
    }
  }

  function matchCommand(text: string) {
    let best: { command: SpeechCommand, score: number } | undefined
    for (const command of commands.value) {
      for (const phrase of command.phrases) {
        const score = similarity(text, phrase)
        if (!best || score >= best.score) best = { command, score }
      }
    }
    return best && best.score >= 0.72 ? best.command : undefined
  }

  function start() {
    if (isListening.value) return
    recognition.value = createSpeechRecognition(true)
    if (!recognition.value) {
      status.value = 'Sprachsteuerung wird von diesem Browser nicht unterstützt.'
      return
    }

    recognition.value.onresult = (event) => {
      const result = event.results[event.results.length - 1]
      const command = result ? matchCommand(result[0]?.transcript || '') : undefined
      if (!command) {
        status.value = 'Nicht verstanden.'
        return
      }
      status.value = `Erkannt: ${command.label}`
      void command.handler()
    }
    recognition.value.onerror = (event) => {
      status.value = `Sprachsteuerung: ${event.error}`
    }
    recognition.value.onend = () => {
      if (isListening.value) recognition.value?.start()
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
    isSupported.value = supportsSpeechRecognition()
  })
  onBeforeUnmount(stop)

  return { commands, isListening, isSupported, status, start, stop, register }
}

export function useSpeechCommands() {
  const commands = inject<SpeechCommands>(speechCommandsKey)
  if (!commands) throw new Error('Speech commands are not available.')
  return commands
}

export function useSpeechCommand(command: SpeechCommand) {
  const { register } = useSpeechCommands()
  onScopeDispose(register(command))
}

export function useSpeechBack(target = '/') {
  useSpeechCommand({
    id: 'back',
    label: 'Zurück',
    phrases: ['zurück', 'zurueck', 'zurückgehen'],
    handler: async () => {
      await navigateTo(target)
    }
  })
}

export function provideSpeechCommands(commands: SpeechCommands) {
  provide(speechCommandsKey, commands)
}
