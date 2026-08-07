type AudioRecordingOptions = {
  onComplete: (recording: Blob) => void | Promise<void>
  onStopping?: () => void
}

export function useAudioRecording(options: AudioRecordingOptions) {
  const recorder = shallowRef<MediaRecorder>()
  const stream = shallowRef<MediaStream>()
  const chunks = ref<Blob[]>([])
  const isRecording = ref(false)
  const silenceDetection = useSilenceDetection(stop)

  async function start() {
    const activeStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const activeRecorder = new MediaRecorder(activeStream)
    let resolveRecording: () => void = () => {}
    const recordingDone = new Promise<void>((resolve) => {
      resolveRecording = resolve
    })

    stream.value = activeStream
    recorder.value = activeRecorder
    chunks.value = []
    activeRecorder.ondataavailable = event => chunks.value.push(event.data)
    activeRecorder.onstop = async () => {
      silenceDetection.stop()
      activeStream.getTracks().forEach(track => track.stop())
      if (stream.value === activeStream) stream.value = undefined
      isRecording.value = false
      try {
        await options.onComplete(new Blob(chunks.value, {
          type: activeRecorder.mimeType || 'audio/webm'
        }))
      } finally {
        resolveRecording()
      }
    }
    activeRecorder.start()
    silenceDetection.start(activeStream)
    isRecording.value = true

    return recordingDone
  }

  function stop() {
    if (recorder.value?.state !== 'recording') return
    options.onStopping?.()
    recorder.value.stop()
  }

  onBeforeUnmount(() => {
    silenceDetection.stop()
    stream.value?.getTracks().forEach(track => track.stop())
  })

  return { isRecording, start, stop }
}
