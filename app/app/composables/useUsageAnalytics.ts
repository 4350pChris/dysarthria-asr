type UsageEvent
  = 'control_activated'
    | 'recording_stopped'
    | 'recording_start_failed'
    | 'recording_resumed'
    | 'text_reset'
    | 'review_action'
    | 'message_copied'
    | 'message_shared'
    | 'message_spoken'
    | 'recording_started'
    | 'training_recording_retried'
    | 'training_recording_saved'
    | 'training_recording_started'
    | 'transcription_completed'
    | 'transcription_failed'
    | 'voice_command_used'
    | 'whatsapp_import_completed'

type UsageEventData = Record<string, boolean | number | string>

/**
 * Sends only a fixed event name and safe metadata. Never send text, audio,
 * names, identifiers, or other personal data to analytics.
 */
export type UsageInput = 'touch' | 'mouse' | 'pen' | 'voice' | 'keyboard_or_assistive' | 'unknown'

export function usageInput(event?: Event | UsageInput): UsageInput {
  if (typeof event === 'string') return event
  if (!event) return 'unknown'
  const pointer = event as PointerEvent
  if (['touch', 'mouse', 'pen'].includes(pointer.pointerType)) return pointer.pointerType as UsageInput
  return event instanceof MouseEvent && event.detail > 0 ? 'mouse' : 'keyboard_or_assistive'
}

export function usageErrorCode(error: unknown): string {
  const name = error instanceof Error ? error.name : ''
  return ['NotAllowedError', 'NotFoundError', 'NotReadableError', 'AbortError', 'NetworkError', 'TimeoutError'].includes(name)
    ? name
    : 'unknown'
}

const previousActivations = new Map<string, number>()

export function useUsageAnalytics() {
  function track(event: UsageEvent, data?: UsageEventData) {
    if (!import.meta.client) return
    // Analytics must never prevent an action, even if the tracker throws synchronously.
    try {
      void Promise.resolve(umTrackEvent(event, data)).catch(() => undefined)
    } catch { /* Tracking is best-effort. */ }
  }

  function control(control: string, input: UsageInput, state: string, ignoreReason = '') {
    const now = Date.now()
    const previous = previousActivations.get(control)
    previousActivations.set(control, now)
    track('control_activated', {
      control, input_method: input, state, accepted: !ignoreReason, ignore_reason: ignoreReason,
      ...(previous === undefined ? {} : { since_previous_ms: Math.max(0, now - previous) })
    })
  }

  return { track, control }
}
