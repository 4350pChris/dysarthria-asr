from __future__ import annotations

import uuid
from random import sample
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..api_errors import field_error
from ..asr import transcribe_german
from ..corpus import create_audio_clip, upsert_transcription_label
from ..paths import AUDIO_DIR, ROOT, TATOEBA_PROMPTS_FILE
from ..training_prompts import find_prompt, prompt_bank

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
    train_prompts = [prompt for prompt in prompt_bank(TATOEBA_PROMPTS_FILE) if prompt["split"] == "train"]
    prompts = sample(train_prompts, k=min(200, len(train_prompts)))
    if not prompts:
        raise HTTPException(status_code=503, detail={"code": "training_prompts_unavailable"})
    return {"prompts": prompts}


@router.post("/recordings")
async def save_training_recording(
    background_tasks: BackgroundTasks,
    prompt_id: str = Form(...),
    audio: UploadFile = File(...),
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
            notes=f"Guided reading: {prompt_id}. Source: {prompt['source']}.",
            training_prompt_id=prompt["id"],
            training_split=prompt["split"],
            training_category=prompt["category"],
            training_prompt_source=prompt["source"],
        )
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    background_tasks.add_task(transcribe_training_recording, audio_id, audio_path)
    return {
        "item": item,
        "prompt": prompt,
    }
