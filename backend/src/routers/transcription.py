from __future__ import annotations

import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, col, select

from ..asr import transcribe_german
from ..candidates import candidate_suggestions
from ..corpus import create_audio_clip, update_transcription_label
from ..database import get_session
from ..emoji_normalizer import emoji_from_spoken_name, replace_spoken_emojis
from ..labeling_models import AudioClipCreate, TranscriptionLabelChanges
from ..math_normalizer import normalize_german_math
from ..models import AsrSource, AudioClip, AudioSource, TranscriptionLabel
from ..paths import AUDIO_DIR, ROOT

router = APIRouter(prefix="/api")


@router.get("/emojis/recent")
def recent_emojis(session: Session = Depends(get_session)) -> list[dict[str, str]]:
    rows = session.exec(
        select(TranscriptionLabel.transcript, TranscriptionLabel.asr_text)
        .join(AudioClip)
        .order_by(col(AudioClip.created_at).desc())
        .limit(1_000)
    ).all()
    emojis: list[dict[str, str]] = []
    seen: set[str] = set()
    for transcript, asr_text in rows:
        match = emoji_from_spoken_name(transcript.strip()) or emoji_from_spoken_name(asr_text.strip())
        if not match or match[0] in seen:
            continue
        seen.add(match[0])
        emojis.append({"value": match[0], "name": match[1]})
        if len(emojis) == 8:
            break
    return emojis


@router.post("/transcribe/partial")
async def transcribe_partial(audio: UploadFile = File(...)) -> dict:
    """Transcribe an in-progress recording without saving audio or text."""
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty audio file.")

    suffix = Path(audio.filename or "").suffix or ".webm"
    with NamedTemporaryFile(suffix=suffix) as temporary_file:
        temporary_file.write(contents)
        temporary_file.flush()
        transcript = transcribe_german(Path(temporary_file.name)).strip()
    return {"raw_transcript": transcript}


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
    emoji_match = emoji_from_spoken_name(transcript)
    math = normalize_german_math(transcript)
    return {
        "audio_id": audio_id,
        "audio_path": relative_audio_path,
        "raw_transcript": transcript,
        "emoji_text": emoji_text,
        "emoji_value": emoji_match[0] if emoji_match else "",
        "emoji_name": emoji_match[1] if emoji_match else "",
        "math_corrected_text": math.corrected_text,
        "math_number_text": math.number_text,
        "math_text": math.math_text,
        "suggestions": candidate_suggestions(transcript, session),
    }
