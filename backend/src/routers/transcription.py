from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..asr import transcribe_german
from ..paths import AUDIO_DIR, ROOT
from ..phrases import phrase_suggestions

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

    transcript = transcribe_german(audio_path)
    return {
        "audio_id": audio_id,
        "audio_path": str(audio_path.relative_to(ROOT)),
        "raw_transcript": transcript,
        "suggestions": phrase_suggestions(transcript),
    }
