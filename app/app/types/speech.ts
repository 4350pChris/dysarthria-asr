export type Suggestion = {
  phrase_number: string
  text: string
  score: number
}

export type TranscriptionResult = {
  audio_id: string
  audio_path: string
  raw_transcript: string
  suggestions: Suggestion[]
}
