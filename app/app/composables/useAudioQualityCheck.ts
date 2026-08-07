import { assessAudioQuality, type AudioQualityReport } from '~/utils/audioQuality'

export function useAudioQualityCheck() {
  async function checkAudio(blob: Blob): Promise<AudioQualityReport> {
    const audioContext = new AudioContext()
    try {
      const audioBuffer = await audioContext.decodeAudioData(await blob.arrayBuffer())
      return assessAudioQuality(
        Array.from({ length: audioBuffer.numberOfChannels }, (_, index) => audioBuffer.getChannelData(index)),
        audioBuffer.sampleRate
      )
    } finally {
      await audioContext.close()
    }
  }

  return { checkAudio }
}
