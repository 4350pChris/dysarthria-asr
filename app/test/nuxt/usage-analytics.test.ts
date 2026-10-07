import { afterEach, expect, it, vi } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { useUsageAnalytics, usageInput, usageErrorCode } from '~/composables/useUsageAnalytics'

const mocks = vi.hoisted(() => ({ track: vi.fn() }))
mockNuxtImport('umTrackEvent', () => mocks.track)
afterEach(() => {
  vi.useRealTimers()
  mocks.track.mockReset()
})

it('sends activation outcomes and intervals without letting tracker failures escape', () => {
  vi.useFakeTimers()
  const analytics = useUsageAnalytics()
  analytics.control('record_toggle', 'touch', 'idle')
  vi.advanceTimersByTime(500)
  analytics.control('record_toggle', 'touch', 'recording', 'cooldown')
  expect(mocks.track).toHaveBeenLastCalledWith('control_activated', {
    control: 'record_toggle', input_method: 'touch', state: 'recording',
    accepted: false, ignore_reason: 'cooldown', since_previous_ms: 500
  })
  mocks.track.mockImplementationOnce(() => {
    throw new Error('tracker unavailable')
  })
  expect(() => analytics.track('recording_started')).not.toThrow()
  expect(usageInput(new PointerEvent('click', { pointerType: 'touch' }))).toBe('touch')
  expect(usageInput(new MouseEvent('click', { detail: 0 }))).toBe('keyboard_or_assistive')
  expect(usageErrorCode(new DOMException('private message', 'NotAllowedError'))).toBe('NotAllowedError')
  expect(usageErrorCode(new Error('private message'))).toBe('unknown')
})
