from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from ..asr import transcribe_german
from ..corpus import (
    audio_file_for_clip,
    create_audio_clip,
    export_labels_csv,
    label_counts,
    next_label_item,
    read_label_items,
    upsert_transcription_label,
)
from ..paths import AUDIO_DIR, ROOT

router = APIRouter(prefix="/api/labeling")

AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".opus", ".wav", ".webm"}


def is_audio_upload(audio: UploadFile) -> bool:
    content_type = audio.content_type or ""
    suffix = Path(audio.filename or "").suffix.lower()
    return content_type.startswith("audio/") or suffix in AUDIO_EXTENSIONS


@router.post("/import")
async def import_audio(files: list[UploadFile] = File(...)) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for audio in files:
        contents = await audio.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Upload non-empty audio files.")
        if not is_audio_upload(audio):
            raise HTTPException(status_code=400, detail="Upload audio files only.")

        suffix = Path(audio.filename or "").suffix.lower() or ".ogg"
        audio_id = uuid.uuid4().hex
        audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
        audio_path.write_bytes(contents)
        relative_audio_path = str(audio_path.relative_to(ROOT))
        create_audio_clip(
            id=audio_id,
            file_path=relative_audio_path,
            original_filename=audio.filename or "",
            content_type=audio.content_type or "",
            source="whatsapp_upload",
        )
        notes = ""
        try:
            asr_text = transcribe_german(audio_path)
        except Exception:
            asr_text = ""
            notes = "ASR failed."
        items.append(
            upsert_transcription_label(
                audio_id=audio_id,
                asr_text=asr_text,
                notes=notes,
            )
        )
    return {"imported": len(items), "items": items, "counts": label_counts()}


@router.get("/items")
def list_items(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    return {
        "items": read_label_items(source=source, status=status, unsure=unsure, limit=limit),
        "counts": label_counts(),
    }


@router.get("/items/next")
def get_next_item(source: str | None = None) -> dict:
    return {"item": next_label_item(source=source), "counts": label_counts()}


@router.patch("/items/{audio_id}")
async def update_item(
    audio_id: str,
    transcript: str = Form(""),
    status: str = Form("draft"),
    unsure: bool = Form(False),
    notes: str = Form(""),
) -> dict:
    return {
        "item": upsert_transcription_label(
            audio_id=audio_id,
            transcript=transcript,
            status=status,
            unsure=unsure,
            notes=notes,
        ),
        "counts": label_counts(),
    }


@router.get("/audio/{audio_id}")
def get_audio(audio_id: str) -> FileResponse:
    return FileResponse(audio_file_for_clip(audio_id, ROOT))


@router.get("/export.csv")
def export_labels(all: bool = False) -> Response:
    return export_labels_csv(all_rows=all)
