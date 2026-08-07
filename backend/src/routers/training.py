from __future__ import annotations

import uuid
from random import sample
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..asr import transcribe_german
from ..corpus import create_audio_clip, upsert_transcription_label
from ..paths import AUDIO_DIR, ROOT, TATOEBA_PROMPTS_FILE
from ..tatoeba import load_prompts, prompt_from_cache

router = APIRouter(prefix="/api/training")


def transcribe_training_recording(audio_id: str, audio_path: Path) -> None:
    try:
        asr_text = transcribe_german(audio_path).strip()
    except Exception:
        return
    if asr_text:
        upsert_transcription_label(
            audio_id=audio_id,
            asr_text=asr_text,
            asr_source="server",
            status="labeled",
        )


@router.get("/prompts")
def list_prompts() -> dict:
    cached_prompts = load_prompts(TATOEBA_PROMPTS_FILE)
    prompts = [
        {"id": f"tatoeba:{prompt['id']}", "text": prompt["text"]}
        for prompt in sample(cached_prompts, k=min(200, len(cached_prompts)))
    ]
    if not prompts:
        raise HTTPException(status_code=503, detail="Reading prompts are not available yet.")
    return {"prompts": prompts}


@router.post("/recordings")
async def save_training_recording(
    background_tasks: BackgroundTasks,
    prompt_id: str = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    if not prompt_id.startswith("tatoeba:"):
        raise HTTPException(status_code=400, detail="Unknown training prompt.")
    prompt = prompt_from_cache(TATOEBA_PROMPTS_FILE, prompt_id.removeprefix("tatoeba:"))
    if not prompt:
        raise HTTPException(status_code=400, detail="Unknown training prompt.")
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty audio file.")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix.lower() or ".webm"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    audio_path.write_bytes(contents)

    try:
        relative_audio_path = str(audio_path.relative_to(ROOT))
        create_audio_clip(
            id=audio_id,
            file_path=relative_audio_path,
            original_filename=f"training-{prompt_id}{suffix}",
            content_type=audio.content_type or "audio/webm",
            source="training_reading",
        )
        item = upsert_transcription_label(
            audio_id=audio_id,
            transcript=prompt["text"],
            status="labeled",
            notes=f"Guided reading: {prompt_id}. Source: Tatoeba.",
        )
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    background_tasks.add_task(transcribe_training_recording, audio_id, audio_path)
    return {
        "item": item,
        "prompt": {"id": prompt_id, "text": prompt["text"], "source": "Tatoeba"},
    }

