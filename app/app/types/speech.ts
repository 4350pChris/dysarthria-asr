export type TranscriptionResult = {
  audio_id: string
  audio_path: string
  raw_transcript: string
  emoji_text: string
  emoji_value: string
  emoji_name: string
  math_corrected_text: string
  math_number_text: string
  math_text: string
}

export type LabelStatus = 'draft' | 'labeled' | 'skipped'
export type AudioSource = 'app_recording' | 'whatsapp_upload' | 'training_reading'

export type ReadingPrompt = {
  id: string
  text: string
  category: string
  source: string
  split: 'train' | 'validation' | 'test'
}

export type LabelItem = {
  audio_id: string
  audio_file: string
  source: AudioSource
  original_filename: string
  content_type: string
  created_at: string
  asr_text: string
  asr_source: 'browser' | 'server'
  transcript: string
  status: LabelStatus
  unsure: boolean
  notes: string
  updated_at: string
}
