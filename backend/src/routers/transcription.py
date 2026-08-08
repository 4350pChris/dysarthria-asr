from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from ..asr import transcribe_german
from ..candidates import candidate_suggestions
from ..corpus import create_audio_clip, update_transcription_label
from ..database import get_session
from ..emoji_normalizer import replace_spoken_emojis
from ..labeling_models import AudioClipCreate, TranscriptionLabelChanges
from ..math_normalizer import normalize_german_math
from ..models import AsrSource, AudioSource
from ..paths import AUDIO_DIR, ROOT

router = APIRouter(prefix="/api")


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix or ".webm"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty audio file.")
    audio_path.write_bytes(contents)

    try:
        transcript = transcribe_german(audio_path).strip()
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    if not transcript:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Keine Sprache erkannt.")

    relative_audio_path = str(audio_path.relative_to(ROOT))
    create_audio_clip(AudioClipCreate(
        id=audio_id,
        file_path=relative_audio_path,
        original_filename=audio.filename or "recording.webm",
        content_type=audio.content_type or "",
        source=AudioSource.APP_RECORDING,
    ), session=session)
    update_transcription_label(
        audio_id,
        TranscriptionLabelChanges(
        asr_text=transcript,
            asr_source=AsrSource.SERVER,
        ), session,
    )
    emoji_text = replace_spoken_emojis(transcript)
    math = normalize_german_math(transcript)
    return {
        "audio_id": audio_id,
        "audio_path": relative_audio_path,
        "raw_transcript": transcript,
        "emoji_text": emoji_text,
        "math_corrected_text": math.corrected_text,
        "math_number_text": math.number_text,
        "math_text": math.math_text,
        "suggestions": candidate_suggestions(transcript, session),
    }
