from __future__ import annotations

import csv
import io
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlmodel import Session
from starlette.background import BackgroundTask

from ..asr import transcribe_german
from ..corpus import (
    audio_file_for_clip,
    count_label_items,
    create_audio_clip,
    delete_audio_clip,
    delete_label_items_without_asr,
    label_counts,
    read_label_items,
    update_transcription_label,
)
from ..database import get_session
from ..labeling_models import AudioClipCreate, TranscriptionLabelChanges
from ..models import AudioSource
from ..paths import AUDIO_DIR, ROOT

router = APIRouter(prefix="/api/labeling")

AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".opus", ".wav", ".webm"}
TRAINING_EXPORT_FIELDS = [
    "audio_id",
    "audio_file",
    "source",
    "original_filename",
    "asr_text",
    "transcript",
    "status",
    "unsure",
    "notes",
    "training_prompt_id",
    "training_split",
    "training_category",
    "training_prompt_source",
    "created_at",
    "updated_at",
]


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


def senders_for_zip(contents: bytes) -> list[str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile as error:
        raise HTTPException(status_code=400, detail="Upload a valid WhatsApp ZIP export.") from error

    names = archive.namelist()
    chat_name = next((name for name in names if Path(name).name.lower().endswith(".txt")), "")
    if not chat_name:
        return []

    audio_names = {
        Path(name).name
        for name in names
        if Path(name).suffix.lower() in AUDIO_EXTENSIONS
    }
    senders = set()
    text = archive.read(chat_name).decode("utf-8", errors="replace")
    for line in text.splitlines():
        sender = chat_sender(line)
        filename = Path(line.rsplit(" ", 1)[-1]).name
        if sender and filename in audio_names:
            senders.add(sender)
    return sorted(senders, key=str.casefold)


def import_audio_bytes(
    contents: bytes,
    original_filename: str,
    content_type: str,
    session: Session,
) -> dict | None:
    suffix = Path(original_filename).suffix.lower() or ".ogg"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    audio_path.write_bytes(contents)
    notes = ""
    try:
        asr_text = transcribe_german(audio_path)
    except Exception:
        asr_text = ""
        notes = "ASR failed."
    if not notes and not asr_text.strip():
        audio_path.unlink(missing_ok=True)
        return None

    relative_audio_path = str(audio_path.relative_to(ROOT))
    create_audio_clip(AudioClipCreate(
        id=audio_id,
        file_path=relative_audio_path,
        original_filename=original_filename,
        content_type=content_type,
        source=AudioSource.WHATSAPP_UPLOAD,
    ), session=session)
    return update_transcription_label(audio_id, TranscriptionLabelChanges(asr_text=asr_text, notes=notes), session)


def import_zip(contents: bytes, target_sender: str, session: Session) -> list[dict | None]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile as error:
        raise HTTPException(status_code=400, detail="Upload a valid WhatsApp ZIP export.") from error

    selected_names = audio_names_for_sender(archive, target_sender)
    items: list[dict | None] = []
    for name in archive.namelist():
        path = Path(name)
        if path.name not in selected_names or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        items.append(
            import_audio_bytes(
                archive.read(name),
                path.name,
                "audio/ogg" if path.suffix.lower() in {".ogg", ".opus"} else "",
                session,
            )
        )
    return items


@router.post("/import")
async def import_audio(
    files: list[UploadFile] = File(...),
    target_sender: str = Form(""),
    session: Session = Depends(get_session),
) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    imported_items: list[dict | None] = []
    for audio in files:
        contents = await audio.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Upload non-empty audio files.")
        if Path(audio.filename or "").suffix.lower() == ".zip":
            imported_items.extend(import_zip(contents, target_sender, session))
            continue
        if not is_audio_upload(audio):
            raise HTTPException(status_code=400, detail="Upload audio files or a WhatsApp ZIP export.")
        imported_items.append(import_audio_bytes(contents, audio.filename or "", audio.content_type or "", session))
    items = [item for item in imported_items if item is not None]
    return {
        "imported": len(items),
        "skipped": len(imported_items) - len(items),
        "items": items,
        "counts": label_counts(session),
    }


@router.post("/import/senders")
async def list_import_senders(archive: UploadFile = File(...)) -> dict:
    if Path(archive.filename or "").suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="Upload a WhatsApp ZIP export.")
    contents = await archive.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty WhatsApp ZIP export.")
    return {"senders": senders_for_zip(contents)}


@router.get("/items")
def list_items(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    missing_asr: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": read_label_items(
            source=source,
            status=status,
            unsure=unsure,
            missing_asr=missing_asr,
            limit=limit, session=session,
        ),
        "filtered_count": count_label_items(
            source=source,
            status=status,
            unsure=unsure,
            missing_asr=missing_asr, session=session,
        ),
        "counts": label_counts(session),
    }


@router.delete("/items/empty-asr")
def delete_empty_asr_items(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    session: Session = Depends(get_session),
) -> dict:
    deleted = delete_label_items_without_asr(
        ROOT,
        source=source,
        status=status,
        unsure=unsure, session=session,
    )
    return {"deleted": deleted, "counts": label_counts(session)}


@router.patch("/items/{audio_id}")
def update_item(
    audio_id: str,
    changes: TranscriptionLabelChanges,
    session: Session = Depends(get_session),
) -> dict:
    return {
        "item": update_transcription_label(
            audio_id,
            changes, session,
        ),
        "counts": label_counts(session),
    }


@router.delete("/items/{audio_id}")
def delete_item(audio_id: str, session: Session = Depends(get_session)) -> dict:
    delete_audio_clip(audio_id, ROOT, session)
    return {"counts": label_counts(session)}


@router.get("/audio/{audio_id}")
def get_audio(audio_id: str, session: Session = Depends(get_session)) -> FileResponse:
    return FileResponse(audio_file_for_clip(audio_id, ROOT, session))


def training_labels_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TRAINING_EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


@router.get("/training-data.zip")
def export_training_data(session: Session = Depends(get_session)) -> FileResponse:
    rows = [
        row
        for row in read_label_items(limit=100000, session=session)
        if (
            row["status"] == "labeled"
            and not row["unsure"]
            and row["transcript"].strip()
            and (row["source"] != "training_reading" or row["training_split"] == "train")
        )
    ]
    if not rows:
        raise HTTPException(status_code=404, detail="No training-ready recordings are available.")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as bundle:
        bundle_path = Path(bundle.name)

    try:
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("training-labels.csv", training_labels_csv(rows))
            archive.writestr(
                "README.txt",
                "This archive contains reviewed training data for dysarthria ASR.\n"
                "Extract it into one directory. training-labels.csv refers to files in data/audio/.\n"
                "Only labeled recordings with a non-empty transcript and no Unsure flag are included.\n"
                "Training readings from validation and test prompt splits are excluded.\n",
            )
            for row in rows:
                audio_path = audio_file_for_clip(row["audio_id"], ROOT, session)
                try:
                    arcname = audio_path.relative_to(ROOT).as_posix()
                except ValueError as error:
                    raise HTTPException(status_code=400, detail="Invalid audio file path.") from error
                archive.write(audio_path, arcname=arcname)
    except Exception:
        bundle_path.unlink(missing_ok=True)
        raise

    return FileResponse(
        bundle_path,
        media_type="application/zip",
        filename="dysarthria-asr-training-data.zip",
        background=BackgroundTask(os.unlink, bundle_path),
    )
