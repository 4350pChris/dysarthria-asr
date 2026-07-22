from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from ..asr import transcribe_german
from ..corpus import (
    audio_file_for_clip,
    create_audio_clip,
    export_labels_csv,
    label_counts,
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


def chat_sender(line: str) -> str:
    message = line.split(" - ", 1)[-1]
    return message.split(":", 1)[0].strip() if ":" in message else ""


def audio_names_for_sender(archive: zipfile.ZipFile, target_sender: str) -> set[str]:
    names = archive.namelist()
    chat_name = next((name for name in names if Path(name).name.lower().endswith(".txt")), "")
    if not target_sender.strip() or not chat_name:
        return {
            Path(name).name
            for name in names
            if Path(name).suffix.lower() in AUDIO_EXTENSIONS
        }

    selected = set()
    target = target_sender.casefold().strip()
    text = archive.read(chat_name).decode("utf-8", errors="replace")
    for line in text.splitlines():
        if chat_sender(line).casefold() != target:
            continue
        filename = Path(line.rsplit(" ", 1)[-1]).name
        if Path(filename).suffix.lower() in AUDIO_EXTENSIONS:
            selected.add(filename)
    return selected


def import_audio_bytes(
    contents: bytes,
    original_filename: str,
    content_type: str,
) -> dict:
    suffix = Path(original_filename).suffix.lower() or ".ogg"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    audio_path.write_bytes(contents)
    relative_audio_path = str(audio_path.relative_to(ROOT))
    create_audio_clip(
        id=audio_id,
        file_path=relative_audio_path,
        original_filename=original_filename,
        content_type=content_type,
        source="whatsapp_upload",
    )
    notes = ""
    try:
        asr_text = transcribe_german(audio_path)
    except Exception:
        asr_text = ""
        notes = "ASR failed."
    return upsert_transcription_label(audio_id=audio_id, asr_text=asr_text, notes=notes)


def import_zip(contents: bytes, target_sender: str) -> list[dict]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile as error:
        raise HTTPException(status_code=400, detail="Upload a valid WhatsApp ZIP export.") from error

    selected_names = audio_names_for_sender(archive, target_sender)
    items = []
    for name in archive.namelist():
        path = Path(name)
        if path.name not in selected_names or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        items.append(
            import_audio_bytes(
                archive.read(name),
                path.name,
                "audio/ogg" if path.suffix.lower() in {".ogg", ".opus"} else "",
            )
        )
    return items


@router.post("/import")
async def import_audio(
    files: list[UploadFile] = File(...),
    target_sender: str = Form(""),
) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for audio in files:
        contents = await audio.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Upload non-empty audio files.")
        if Path(audio.filename or "").suffix.lower() == ".zip":
            items.extend(import_zip(contents, target_sender))
            continue
        if not is_audio_upload(audio):
            raise HTTPException(status_code=400, detail="Upload audio files or a WhatsApp ZIP export.")
        items.append(import_audio_bytes(contents, audio.filename or "", audio.content_type or ""))
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
