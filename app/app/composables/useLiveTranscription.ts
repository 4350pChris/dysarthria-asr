type LiveTranscriptionOptions = {
  onText: (text: string) => void
}

export function useLiveTranscription(options: LiveTranscriptionOptions) {
  let context: AudioContext | undefined
  let socket: WebSocket | undefined
  let source: MediaStreamAudioSourceNode | undefined
  let processor: AudioWorkletNode | undefined

  async function start(stream: MediaStream) {
    try {
      const queuedFrames: ArrayBuffer[] = []
      context = new AudioContext({ sampleRate: 16_000 })
      await context.audioWorklet.addModule('/pcm-capture.js')
      socket = new WebSocket(streamUrl(context.sampleRate))
      socket.binaryType = 'arraybuffer'
      source = context.createMediaStreamSource(stream)
      processor = new AudioWorkletNode(context, 'pcm-capture')
      processor.port.onmessage = (event) => {
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(event.data)
        } else if (queuedFrames.length < 250) {
          queuedFrames.push(event.data)
        }
      }
      socket.onopen = () => queuedFrames.splice(0).forEach(frame => socket?.send(frame))
      source.connect(processor).connect(context.destination)
      socket.onmessage = (event) => {
        const message: unknown = JSON.parse(event.data)
        if (!message || typeof message !== 'object') return
        const { committed, partial, type } = message as Record<string, unknown>
        if (type === 'partial' && typeof committed === 'string' && typeof partial === 'string') {
          options.onText([committed, partial].filter(Boolean).join(' '))
        }
      }
    } catch {
      stop()
    }
  }

  function stop() {
    processor?.disconnect()
    source?.disconnect()
    socket?.close()
    void context?.close()
    processor = undefined
    source = undefined
    socket = undefined
    context = undefined
  }

  onScopeDispose(stop)

  return { start, stop }
}

function streamUrl(sampleRate: number) {
  const apiBase = useRuntimeConfig().public.apiBase
  const url = new URL(apiBase)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/$/, '')}/api/transcribe/stream`
  url.searchParams.set('sample_rate', String(sampleRate))
  return url.toString()
}
