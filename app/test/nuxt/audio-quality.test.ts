import { describe, expect, it } from 'vitest'
import { assessAudioQuality } from '~/utils/audioQuality'

describe('assessAudioQuality', () => {
  it('blocks silent audio', () => {
    const report = assessAudioQuality([new Float32Array(16_000)], 16_000)

    expect(report.canSave).toBe(false)
    expect(report.issues.map(issue => issue.code)).toContain('no_speech')
  })

  it('warns about clipping and a long pause without blocking the save', () => {
    const samples = new Float32Array(96_000)
    samples.fill(0.1, 0, 16_000)
    samples[0] = 1
    const report = assessAudioQuality([samples], 16_000)

    expect(report.canSave).toBe(true)
    expect(report.issues.map(issue => issue.code)).toEqual(expect.arrayContaining(['clipping', 'long_silence']))
  })
})
