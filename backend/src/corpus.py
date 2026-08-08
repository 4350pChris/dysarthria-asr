from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from .database import connect_db

AUDIO_SOURCES = {"app_recording", "whatsapp_upload", "training_reading"}
ASR_SOURCES = {"browser", "server"}
LABEL_STATUSES = {"draft", "labeled", "skipped"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_audio_clip(
    id: str,
    file_path: str,
    original_filename: str = "",
    content_type: str = "",
    source: str = "whatsapp_upload",
) -> dict:
    if source not in AUDIO_SOURCES:
        raise HTTPException(status_code=400, detail="Invalid audio source.")
    created_at = now()
    with connect_db() as db:
        db.execute(
            """
            INSERT INTO audio_clips (
                id,
                file_path,
                original_filename,
                content_type,
                source,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                id,
                file_path,
                original_filename,
                content_type,
                source,
                created_at,
            ),
        )
    return {
        "id": id,
        "file_path": file_path,
        "original_filename": original_filename,
        "content_type": content_type,
        "source": source,
        "created_at": created_at,
    }


def upsert_transcription_label(
    audio_id: str,
    asr_text: str | None = None,
    asr_source: str | None = None,
    transcript: str | None = None,
    status: str = "draft",
    unsure: bool = False,
    notes: str | None = None,
    training_prompt_id: str | None = None,
    training_split: str | None = None,
    training_category: str | None = None,
    training_prompt_source: str | None = None,
) -> dict:
    if status not in LABEL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid label status.")
    if asr_source is not None and asr_source not in ASR_SOURCES:
        raise HTTPException(status_code=400, detail="Invalid ASR source.")
    updated_at = now()
    with connect_db() as db:
        audio = db.execute("SELECT id FROM audio_clips WHERE id = ?", (audio_id,)).fetchone()
        if not audio:
            raise HTTPException(status_code=404, detail="Audio clip not found.")
        db.execute(
            """
            INSERT OR IGNORE INTO transcription_labels (audio_id, updated_at)
            VALUES (?, ?)
            """,
            (audio_id, updated_at),
        )
        fields = ["status = ?", "unsure = ?", "updated_at = ?"]
        args: list[str | int] = [status, int(unsure), updated_at]
        if asr_text is not None:
            fields.append("asr_text = ?")
            args.append(asr_text)
        if asr_source is not None:
            fields.append("asr_source = ?")
            args.append(asr_source)
        if transcript is not None:
            fields.append("transcript = ?")
            args.append(transcript)
        if notes is not None:
            fields.append("notes = ?")
            args.append(notes)
        for field, value in {
            "training_prompt_id": training_prompt_id,
            "training_split": training_split,
            "training_category": training_category,
            "training_prompt_source": training_prompt_source,
        }.items():
            if value is not None:
                fields.append(f"{field} = ?")
                args.append(value)
        args.append(audio_id)
        db.execute(
            f"""
            UPDATE transcription_labels
            SET {', '.join(fields)}
            WHERE audio_id = ?
            """,
            args,
        )
    return read_label_item(audio_id)


def read_label_item(audio_id: str) -> dict:
    with connect_db() as db:
        row = db.execute(
            """
            SELECT
                audio_clips.id AS audio_id,
                audio_clips.file_path AS audio_file,
                audio_clips.source,
                audio_clips.original_filename,
                audio_clips.content_type,
                audio_clips.created_at,
                transcription_labels.asr_text,
                transcription_labels.asr_source,
                transcription_labels.transcript,
                transcription_labels.status,
                transcription_labels.unsure,
                transcription_labels.notes,
                transcription_labels.training_prompt_id,
                transcription_labels.training_split,
                transcription_labels.training_category,
                transcription_labels.training_prompt_source,
                transcription_labels.updated_at
            FROM audio_clips
            JOIN transcription_labels ON transcription_labels.audio_id = audio_clips.id
            WHERE audio_clips.id = ?
            """,
            (audio_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Label item not found.")
    item = dict(row)
    item["unsure"] = bool(item["unsure"])
    return item


def label_item_filters(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    missing_asr: bool | None = None,
) -> tuple[str, list[str | int]]:
    conditions = []
    args: list[str | int] = []
    if source:
        conditions.append("audio_clips.source = ?")
        args.append(source)
    if status:
        conditions.append("transcription_labels.status = ?")
        args.append(status)
    if unsure is not None:
        conditions.append("transcription_labels.unsure = ?")
        args.append(int(unsure))
    if missing_asr:
        conditions.append("TRIM(transcription_labels.asr_text) = ''")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, args


def read_label_items(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    missing_asr: bool | None = None,
    limit: int = 100,
) -> list[dict]:
    where, args = label_item_filters(source, status, unsure, missing_asr)
    args.append(limit)
    with connect_db() as db:
        rows = db.execute(
            f"""
            SELECT
                audio_clips.id AS audio_id,
                audio_clips.file_path AS audio_file,
                audio_clips.source,
                audio_clips.original_filename,
                audio_clips.content_type,
                audio_clips.created_at,
                transcription_labels.asr_text,
                transcription_labels.asr_source,
                transcription_labels.transcript,
                transcription_labels.status,
                transcription_labels.unsure,
                transcription_labels.notes,
                transcription_labels.training_prompt_id,
                transcription_labels.training_split,
                transcription_labels.training_category,
                transcription_labels.training_prompt_source,
                transcription_labels.updated_at
            FROM audio_clips
            JOIN transcription_labels ON transcription_labels.audio_id = audio_clips.id
            {where}
            ORDER BY audio_clips.created_at ASC, audio_clips.id ASC
            LIMIT ?
            """,
            args,
        ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["unsure"] = bool(item["unsure"])
    return items


def count_label_items(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    missing_asr: bool | None = None,
) -> int:
    where, args = label_item_filters(source, status, unsure, missing_asr)
    with connect_db() as db:
        row = db.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM audio_clips
            JOIN transcription_labels ON transcription_labels.audio_id = audio_clips.id
            {where}
            """,
            args,
        ).fetchone()
    return row["count"]


def delete_label_items_without_asr(
    root: Path,
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
) -> int:
    deleted = 0
    while True:
        items = read_label_items(
            source=source,
            status=status,
            unsure=unsure,
            missing_asr=True,
            limit=500,
        )
        if not items:
            return deleted
        for item in items:
            delete_audio_clip(item["audio_id"], root)
        deleted += len(items)


def label_counts() -> dict:
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM transcription_labels
            GROUP BY status
            """
        ).fetchall()
    counts = {"draft": 0, "labeled": 0, "skipped": 0}
    counts.update({row["status"]: row["count"] for row in rows})
    counts["total"] = sum(counts.values())
    return counts


def audio_file_for_clip(audio_id: str, root: Path) -> Path:
    with connect_db() as db:
        row = db.execute("SELECT file_path FROM audio_clips WHERE id = ?", (audio_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio clip not found.")
    path = root / row["file_path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return path


def delete_audio_clip(audio_id: str, root: Path) -> None:
    with connect_db() as db:
        row = db.execute(
            "SELECT file_path FROM audio_clips WHERE id = ?", (audio_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio clip not found.")

    audio_path = (root / row["file_path"]).resolve()
    try:
        audio_path.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audio file path.")

    with connect_db() as db:
        db.execute("DELETE FROM audio_clips WHERE id = ?", (audio_id,))
    audio_path.unlink(missing_ok=True)
