type UsageEvent
  = 'category_created'
    | 'message_copied'
    | 'message_shared'
    | 'message_spoken'
    | 'phrase_created'
    | 'phrase_selected'
    | 'phrase_updated'
    | 'recording_started'
    | 'suggestion_selected'
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
export function useUsageAnalytics() {
  function track(event: UsageEvent, data?: UsageEventData) {
    if (!import.meta.client) return
    void Promise.resolve(umTrackEvent(event, data)).catch(() => undefined)
  }

  return { track }
}
