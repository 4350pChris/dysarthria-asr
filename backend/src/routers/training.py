from __future__ import annotations

import uuid
from pathlib import Path
from random import sample
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlmodel import Session

from .. import database
from ..api_errors import field_error
from ..asr import transcribe_german
from ..corpus import create_audio_clip, update_transcription_label
from ..database import get_session
from ..labeling_models import AudioClipCreate, TranscriptionLabelChanges
from ..models import AsrSource, AudioSource, LabelStatus
from ..paths import AUDIO_DIR, ROOT, TATOEBA_PROMPTS_FILE
from ..training_prompts import find_prompt, prompt_bank
from ..validation import CleanText

router = APIRouter(prefix="/api/training")


def transcribe_training_recording(audio_id: str, audio_path: Path) -> None:
    try:
        asr_text = transcribe_german(audio_path).strip()
    except Exception:
        return
    if asr_text:
        with Session(database.engine, expire_on_commit=False) as session:
            update_transcription_label(
                audio_id,
                TranscriptionLabelChanges(
                    asr_text=asr_text,
                    asr_source=AsrSource.SERVER,
                    status=LabelStatus.LABELED,
                ),
                session,
            )


@router.get("/prompts")
def list_prompts() -> dict:
    train_prompts = [prompt for prompt in prompt_bank(TATOEBA_PROMPTS_FILE) if prompt["split"] == "train"]
    prompts = sample(train_prompts, k=min(200, len(train_prompts)))
    if not prompts:
        raise HTTPException(status_code=503, detail={"code": "training_prompts_unavailable"})
    return {"prompts": prompts}


@router.post("/recordings")
async def save_training_recording(
    background_tasks: BackgroundTasks,
    prompt_id: Annotated[CleanText, Form()],
    audio: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    prompt = find_prompt(TATOEBA_PROMPTS_FILE, prompt_id)
    if not prompt or prompt["split"] != "train":
        raise field_error(404, "prompt_id", "training_prompt_not_found")
    contents = await audio.read()
    if not contents:
        raise field_error(422, "audio", "audio_required")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix.lower() or ".webm"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    audio_path.write_bytes(contents)

    try:
        relative_audio_path = str(audio_path.relative_to(ROOT))
        create_audio_clip(AudioClipCreate(
            id=audio_id,
            file_path=relative_audio_path,
            original_filename=f"training-{prompt_id}{suffix}",
            content_type=audio.content_type or "audio/webm",
            source=AudioSource.TRAINING_READING,
        ), session=session)
        item = update_transcription_label(
            audio_id,
            TranscriptionLabelChanges(
                transcript=prompt["text"],
                status=LabelStatus.LABELED,
                notes=f"Guided reading: {prompt_id}. Source: {prompt['source']}.",
                training_prompt_id=prompt["id"],
                training_split=prompt["split"],
                training_category=prompt["category"],
                training_prompt_source=prompt["source"],
            ),
            session,
        )
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    background_tasks.add_task(transcribe_training_recording, audio_id, audio_path)
    return {
        "item": item,
        "prompt": prompt,
    }
