from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, col, select

from .database import commit
from .labeling_models import AudioClipCreate, TranscriptionLabelChanges
from .models import AudioClip, LabelStatus, TranscriptionLabel


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_audio_clip(clip_data: AudioClipCreate, session: Session) -> dict:
    clip = AudioClip(**clip_data.model_dump(), created_at=now())
    session.add(clip)
    commit(session)
    return clip.model_dump()


def update_transcription_label(audio_id: str, changes: TranscriptionLabelChanges, session: Session) -> dict:
    if session.get(AudioClip, audio_id) is None:
        raise HTTPException(status_code=404, detail="Audio clip not found.")
    label = session.exec(select(TranscriptionLabel).where(col(TranscriptionLabel.audio_id) == audio_id)).first()
    if label is None:
        label = TranscriptionLabel(audio_id=audio_id, updated_at=now())
        session.add(label)
    for field, value in changes.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(label, field, value)
    label.updated_at = now()
    commit(session)
    return read_label_item(audio_id, session)




def _item(clip: AudioClip, label: TranscriptionLabel) -> dict:
    return {"audio_id": clip.id, "audio_file": clip.file_path, "source": clip.source, "original_filename": clip.original_filename, "content_type": clip.content_type, "created_at": clip.created_at, "asr_text": label.asr_text, "asr_source": label.asr_source, "transcript": label.transcript, "status": label.status, "unsure": label.unsure, "notes": label.notes, "training_prompt_id": label.training_prompt_id, "training_split": label.training_split, "training_category": label.training_category, "training_prompt_source": label.training_prompt_source, "updated_at": label.updated_at}


def _filtered_statement(source: str | None, status: str | None, unsure: bool | None, missing_asr: bool | None):
    statement = select(AudioClip, TranscriptionLabel).join(TranscriptionLabel)
    if source:
        statement = statement.where(col(AudioClip.source) == source)
    if status:
        statement = statement.where(col(TranscriptionLabel.status) == status)
    if unsure is not None:
        statement = statement.where(col(TranscriptionLabel.unsure) == unsure)
    if missing_asr:
        statement = statement.where(func.trim(col(TranscriptionLabel.asr_text)) == "")
    return statement


def read_label_item(audio_id: str, session: Session) -> dict:
    row = session.exec(select(AudioClip, TranscriptionLabel).join(TranscriptionLabel).where(col(AudioClip.id) == audio_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Label item not found.")
    return _item(*row)


def read_label_items(source: str | None = None, status: str | None = None, unsure: bool | None = None, missing_asr: bool | None = None, limit: int = 100, *, session: Session) -> list[dict]:
    rows = session.exec(_filtered_statement(source, status, unsure, missing_asr).order_by(col(AudioClip.created_at), col(AudioClip.id)).limit(limit)).all()
    return [_item(*row) for row in rows]


def count_label_items(source: str | None = None, status: str | None = None, unsure: bool | None = None, missing_asr: bool | None = None, *, session: Session) -> int:
    return len(read_label_items(source, status, unsure, missing_asr, limit=1000000, session=session))


def delete_label_items_without_asr(root: Path, source: str | None = None, status: str | None = None, unsure: bool | None = None, *, session: Session) -> int:
    items = read_label_items(source, status, unsure, True, limit=1000000, session=session)
    for item in items:
        delete_audio_clip(item["audio_id"], root, session)
    return len(items)


def label_counts(session: Session) -> dict:
    items = read_label_items(limit=1000000, session=session)
    counts = {status.value: 0 for status in LabelStatus}
    for item in items:
        counts[item["status"]] += 1
    return {"total": sum(counts.values()), **counts}


def audio_file_for_clip(audio_id: str, root: Path, session: Session) -> Path:
    clip = session.get(AudioClip, audio_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Audio clip not found.")
    path = root / clip.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return path


def delete_audio_clip(audio_id: str, root: Path, session: Session) -> None:
    clip = session.get(AudioClip, audio_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Audio clip not found.")
    path = (root / clip.file_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid audio file path.") from error
    session.delete(clip)
    commit(session)
    path.unlink(missing_ok=True)
