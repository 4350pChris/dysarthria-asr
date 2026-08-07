export type AudioQualityIssue = {
  code: 'too_short' | 'no_speech' | 'quiet' | 'loud' | 'clipping' | 'long_silence'
  level: 'error' | 'warning'
  message: string
}

export type AudioQualityReport = {
  canSave: boolean
  issues: AudioQualityIssue[]
}

const SILENCE_RMS = 0.006
const FRAME_DURATION_SECONDS = 0.1

export function assessAudioQuality(
  channels: readonly Float32Array[],
  sampleRate: number
): AudioQualityReport {
  const samples = channels[0]?.length ?? 0
  const duration = samples / sampleRate
  const issues: AudioQualityIssue[] = []

  if (duration < 1) {
    issues.push({
      code: 'too_short',
      level: 'error',
      message: 'Die Aufnahme ist zu kurz. Bitte nimm den ganzen Text auf.'
    })
  }

  let sumOfSquares = 0
  let peak = 0
  let clippedSamples = 0
  let sampleCount = 0
  const frameSize = Math.max(1, Math.round(sampleRate * FRAME_DURATION_SECONDS))
  let silentFrames = 0
  let longestSilentFrames = 0

  for (let start = 0; start < samples; start += frameSize) {
    let frameSumOfSquares = 0
    let frameSampleCount = 0
    for (let index = start; index < Math.min(start + frameSize, samples); index++) {
      for (const channel of channels) {
        const sample = channel[index] ?? 0
        const absoluteSample = Math.abs(sample)
        frameSumOfSquares += sample * sample
        sumOfSquares += sample * sample
        peak = Math.max(peak, absoluteSample)
        if (absoluteSample >= 0.99) clippedSamples += 1
        frameSampleCount += 1
        sampleCount += 1
      }
    }

    const frameRms = Math.sqrt(frameSumOfSquares / Math.max(1, frameSampleCount))
    if (frameRms < SILENCE_RMS) {
      silentFrames += 1
      longestSilentFrames = Math.max(longestSilentFrames, silentFrames)
    } else {
      silentFrames = 0
    }
  }

  const rms = Math.sqrt(sumOfSquares / Math.max(1, sampleCount))
  if (rms < 0.001) {
    issues.push({
      code: 'no_speech',
      level: 'error',
      message: 'Die Aufnahme enthält kein nutzbares Signal. Bitte prüfe das Mikrofon und nimm erneut auf.'
    })
  } else if (rms < 0.01) {
    issues.push({
      code: 'quiet',
      level: 'warning',
      message: 'Die Aufnahme ist sehr leise. Höre sie vor dem Speichern an.'
    })
  } else if (rms > 0.5) {
    issues.push({
      code: 'loud',
      level: 'warning',
      message: 'Die Aufnahme ist sehr laut. Höre sie vor dem Speichern an.'
    })
  }

  if (clippedSamples / Math.max(1, sampleCount) > 0.001 || peak >= 1) {
    issues.push({
      code: 'clipping',
      level: 'warning',
      message: 'Das Signal ist übersteuert. Eine neue Aufnahme kann besser sein.'
    })
  }

  if (longestSilentFrames * FRAME_DURATION_SECONDS >= 4) {
    issues.push({
      code: 'long_silence',
      level: 'warning',
      message: 'Die Aufnahme enthält eine lange Pause. Höre sie vor dem Speichern an.'
    })
  }

  return {
    canSave: !issues.some(issue => issue.level === 'error'),
    issues
  }
}
