from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..audio_samples import create_audio_sample
from ..asr import transcribe_german
from ..candidates import candidate_suggestions
from ..math_normalizer import normalize_german_math
from ..paths import AUDIO_DIR, ROOT

router = APIRouter(prefix="/api")


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix or ".webm"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty audio file.")
    audio_path.write_bytes(contents)
    relative_audio_path = str(audio_path.relative_to(ROOT))
    create_audio_sample(
        id=audio_id,
        file_path=relative_audio_path,
        content_type=audio.content_type or "",
    )

    transcript = transcribe_german(audio_path)
    math = normalize_german_math(transcript)
    return {
        "audio_id": audio_id,
        "audio_path": relative_audio_path,
        "raw_transcript": transcript,
        "math_corrected_text": math.corrected_text,
        "math_number_text": math.number_text,
        "math_text": math.math_text,
        "suggestions": candidate_suggestions(transcript),
    }
