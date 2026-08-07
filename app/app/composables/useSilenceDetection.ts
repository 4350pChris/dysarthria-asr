const MIN_DURATION_MS = 1500
const SILENCE_MS = 2000
const MAX_DURATION_MS = 30000
const SILENCE_THRESHOLD = 0.025

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

  function start(stream: MediaStream) {
    stop()
    stopped.value = false
    startedAt.value = performance.now()
    silentSince.value = undefined

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

      if (elapsed >= MAX_DURATION_MS) {
        stop()
        onStop()
        return
      }

      if (elapsed >= MIN_DURATION_MS && rms < SILENCE_THRESHOLD) {
        silentSince.value ??= now
        if (now - silentSince.value >= SILENCE_MS) {
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
