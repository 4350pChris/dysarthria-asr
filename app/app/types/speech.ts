export type Suggestion = {
  phrase_id: number
  text: string
  score: number
}

export type Phrase = {
  id: number
  category: string
  text: string
}

export type Category = {
  id: number
  name: string
  phrase_count: number
}

export type TranscriptionResult = {
  audio_id: string
  audio_path: string
  raw_transcript: string
  suggestions: Suggestion[]
}
