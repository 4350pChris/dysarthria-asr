type SilenceDetectionOptions = {
  minDurationMs?: number
  silenceMs?: number
  maxDurationMs?: number
  threshold?: number
}

export function useSilenceDetection(onStop: () => void) {
  const frame = ref<number>()
  const audioContext = shallowRef<AudioContext>()
  const startedAt = ref(0)
  const silentSince = ref<number>()
  const stopped = ref(false)

  function stop() {
    stopped.value = true
    if (frame.value) {
      cancelAnimationFrame(frame.value)
      frame.value = undefined
    }
    void audioContext.value?.close()
    audioContext.value = undefined
  }

  function start(stream: MediaStream, options: SilenceDetectionOptions = {}) {
    stop()
    stopped.value = false
    startedAt.value = performance.now()
    silentSince.value = undefined

    const minDurationMs = options.minDurationMs ?? 1500
    const silenceMs = options.silenceMs ?? 2000
    const maxDurationMs = options.maxDurationMs ?? 10000
    const threshold = options.threshold ?? 0.025

    audioContext.value = new AudioContext()
    const source = audioContext.value.createMediaStreamSource(stream)
    const analyser = audioContext.value.createAnalyser()
    analyser.fftSize = 2048
    source.connect(analyser)

    const data = new Uint8Array(analyser.fftSize)

    function tick() {
      if (stopped.value) return

      analyser.getByteTimeDomainData(data)
      const rms = Math.sqrt(
        data.reduce((sum, value) => {
          const centered = (value - 128) / 128
          return sum + centered * centered
        }, 0) / data.length
      )

      const now = performance.now()
      const elapsed = now - startedAt.value

      if (elapsed >= maxDurationMs) {
        stop()
        onStop()
        return
      }

      if (elapsed >= minDurationMs && rms < threshold) {
        silentSince.value ??= now
        if (now - silentSince.value >= silenceMs) {
          stop()
          onStop()
          return
        }
      } else {
        silentSince.value = undefined
      }

      frame.value = requestAnimationFrame(tick)
    }

    tick()
  }

  onBeforeUnmount(stop)

  return {
    start,
    stop
  }
}
