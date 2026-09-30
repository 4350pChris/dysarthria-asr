type AudioRecordingOptions = {
  onComplete: (recording: Blob) => void | Promise<void>
  autoStopOnSilence?: Ref<boolean>
  withAudioLevel?: boolean
  onStream?: (stream: MediaStream) => void
  onStopping?: () => void
}

export function useAudioRecording(options: AudioRecordingOptions) {
  const recorder = shallowRef<MediaRecorder>()
  const stream = shallowRef<MediaStream>()
  const chunks = ref<Blob[]>([])
  const isRecording = ref(false)
  const audioLevel = ref(0)
  const silenceDetection = useSilenceDetection(stop, () => options.autoStopOnSilence?.value ?? true)
  let levelContext: AudioContext | undefined
  let levelSource: MediaStreamAudioSourceNode | undefined
  let levelFrame = 0

  function startLevelMeter(activeStream: MediaStream) {
    levelContext = new AudioContext()
    const analyser = levelContext.createAnalyser()
    const silentGain = levelContext.createGain()
    const samples = new Uint8Array(analyser.fftSize)
    levelSource = levelContext.createMediaStreamSource(activeStream)
    silentGain.gain.value = 0
    levelSource.connect(analyser).connect(silentGain).connect(levelContext.destination)

    const updateLevel = () => {
      analyser.getByteTimeDomainData(samples)
      const meanSquare = samples.reduce((sum, sample) => {
        const normalized = (sample - 128) / 128
        return sum + normalized * normalized
      }, 0) / samples.length
      audioLevel.value = Math.min(1, Math.sqrt(meanSquare) * 6)
      levelFrame = requestAnimationFrame(updateLevel)
    }
    updateLevel()
  }

  function stopLevelMeter() {
    cancelAnimationFrame(levelFrame)
    levelSource?.disconnect()
    void levelContext?.close()
    levelContext = undefined
    levelSource = undefined
    audioLevel.value = 0
  }

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
    if (options.withAudioLevel) startLevelMeter(activeStream)
    activeRecorder.ondataavailable = event => chunks.value.push(event.data)
    activeRecorder.onstop = async () => {
      silenceDetection.stop()
      stopLevelMeter()
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
    options.onStream?.(activeStream)
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
    stopLevelMeter()
    stream.value?.getTracks().forEach(track => track.stop())
  })

  return { audioLevel, isRecording, start, stop }
}
