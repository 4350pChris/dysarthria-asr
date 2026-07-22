export type Suggestion = {
  id: string
  source: 'phrase' | 'generated'
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
  math_corrected_text: string
  math_number_text: string
  math_text: string
  suggestions: Suggestion[]
}

export type LabelStatus = 'draft' | 'labeled' | 'skipped'
export type AudioSource = 'app_recording' | 'whatsapp_upload'

export type LabelItem = {
  audio_id: string
  audio_file: string
  source: AudioSource
  original_filename: string
  content_type: string
  created_at: string
  asr_text: string
  transcript: string
  status: LabelStatus
  unsure: boolean
  notes: string
  updated_at: string
}
