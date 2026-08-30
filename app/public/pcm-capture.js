class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const input = inputs[0]?.[0]
    if (!input) return true
    const samples = new Int16Array(input.length)
    for (let index = 0; index < input.length; index++) {
      samples[index] = Math.max(-1, Math.min(1, input[index])) * 0x7fff
    }
    this.port.postMessage(samples.buffer, [samples.buffer])
    outputs[0]?.[0]?.fill(0)
    return true
  }
}

registerProcessor('pcm-capture', PcmCaptureProcessor)
