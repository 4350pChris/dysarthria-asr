import {
  createSpeechRecognition,
  supportsSpeechRecognition,
  type SpeechRecognition
} from '../utils/speechRecognition'

export function useBrowserTranscript() {
  const isSupported = ref(false)
  let recognition: SpeechRecognition | undefined
  let transcript = ''
  let finish: ((transcript: string | undefined) => void) | undefined
  let finished = false
  let result: Promise<string | undefined> = Promise.resolve(undefined)
  let stopTimer: ReturnType<typeof setTimeout> | undefined

  function complete() {
    if (finished) return
    finished = true
    if (stopTimer) clearTimeout(stopTimer)
    stopTimer = undefined
    finish?.(transcript || undefined)
  }

  function start() {
    recognition = createSpeechRecognition(true)
    if (!recognition) return Promise.resolve(undefined)

    transcript = ''
    finished = false
    result = new Promise((resolve) => {
      finish = resolve
    })
    recognition.onresult = (event) => {
      const parts: string[] = []
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const item = event.results[index]
        if (item?.isFinal && item[0]?.transcript) parts.push(item[0].transcript.trim())
      }
      transcript = [transcript, ...parts].filter(Boolean).join(' ')
    }
    recognition.onerror = () => complete()
    recognition.onend = complete

    try {
      recognition.start()
    } catch {
      complete()
    }
    return result
  }

  function stop() {
    if (!recognition || finished) return result
    stopTimer = setTimeout(complete, 1500)
    try {
      recognition.stop()
    } catch {
      complete()
    }
    return result
  }

  onMounted(() => {
    isSupported.value = supportsSpeechRecognition()
  })

  onBeforeUnmount(stop)

  return { isSupported, start, stop }
}
