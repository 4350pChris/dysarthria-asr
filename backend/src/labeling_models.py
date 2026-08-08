from pydantic import BaseModel

from .models import AsrSource, AudioSource, LabelStatus


class AudioClipCreate(BaseModel):
    id: str
    file_path: str
    original_filename: str = ""
    content_type: str = ""
    source: AudioSource = AudioSource.WHATSAPP_UPLOAD


class TranscriptionLabelChanges(BaseModel):
    asr_text: str | None = None
    asr_source: AsrSource | None = None
    transcript: str | None = None
    status: LabelStatus | None = None
    unsure: bool | None = None
    notes: str | None = None
    training_prompt_id: str | None = None
    training_split: str | None = None
    training_category: str | None = None
    training_prompt_source: str | None = None
