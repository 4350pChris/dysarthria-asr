from __future__ import annotations

import uuid
from random import sample
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..corpus import create_audio_clip, upsert_transcription_label
from ..paths import AUDIO_DIR, ROOT, TATOEBA_PROMPTS_FILE
from ..tatoeba import load_prompts, prompt_from_cache
from ..training_prompts import TrainingPrompt, prompt_by_id, prompts_for_topic, topics

router = APIRouter(prefix="/api/training")


def prompt_payload(prompt) -> dict:
    return {"id": prompt.id, "topic": prompt.topic, "text": prompt.text, "source": prompt.source}


@router.get("/topics")
def list_topics() -> dict:
    available_topics = topics()
    if load_prompts(TATOEBA_PROMPTS_FILE):
        available_topics.append("Tatoeba")
    return {"topics": available_topics}


@router.get("/prompts")
def list_prompts(topic: str) -> dict:
    if topic == "Tatoeba":
        cached_prompts = load_prompts(TATOEBA_PROMPTS_FILE)
        prompts = [
            {"id": f"tatoeba:{prompt['id']}", "topic": topic, "text": prompt["text"], "source": "Tatoeba"}
            for prompt in sample(cached_prompts, k=min(200, len(cached_prompts)))
        ]
        if not prompts:
            raise HTTPException(status_code=404, detail="Tatoeba prompts have not been imported yet.")
        return {"prompts": prompts}
    prompts = prompts_for_topic(topic)
    if not prompts:
        raise HTTPException(status_code=404, detail="Unknown training topic.")
    return {"prompts": [prompt_payload(prompt) for prompt in prompts]}


@router.post("/recordings")
async def save_training_recording(
    prompt_id: str = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    is_tatoeba_prompt = prompt_id.startswith("tatoeba:")
    if is_tatoeba_prompt:
        cached = prompt_from_cache(TATOEBA_PROMPTS_FILE, prompt_id.removeprefix("tatoeba:"))
        prompt = (
            None
            if cached is None
            else TrainingPrompt(
                id=prompt_id,
                topic="Tatoeba",
                text=cached["text"],
                source="Tatoeba",
            )
        )
    else:
        prompt = prompt_by_id(prompt_id)
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
            original_filename=f"training-{prompt.id}{suffix}",
            content_type=audio.content_type or "audio/webm",
            source="training_reading",
        )
        item = upsert_transcription_label(
            audio_id=audio_id,
            transcript=prompt.text,
            status="labeled",
            notes=f"Guided reading: {prompt.id}. Source: {prompt.source}.",
        )
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    return {"item": item, "prompt": prompt_payload(prompt)}
