from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response

from .database import connect_db

AUDIO_SOURCES = {"app_recording", "whatsapp_upload"}
LABEL_STATUSES = {"draft", "labeled", "skipped"}
EXPORT_FIELDS = [
    "audio_id",
    "audio_file",
    "source",
    "original_filename",
    "asr_text",
    "transcript",
    "status",
    "unsure",
    "notes",
    "created_at",
    "updated_at",
]


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
    transcript: str | None = None,
    status: str = "draft",
    unsure: bool = False,
    notes: str | None = None,
) -> dict:
    if status not in LABEL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid label status.")
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
        if transcript is not None:
            fields.append("transcript = ?")
            args.append(transcript)
        if notes is not None:
            fields.append("notes = ?")
            args.append(notes)
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
                transcription_labels.transcript,
                transcription_labels.status,
                transcription_labels.unsure,
                transcription_labels.notes,
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


def read_label_items(
    source: str | None = None,
    status: str | None = None,
    unsure: bool | None = None,
    limit: int = 100,
) -> list[dict]:
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
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
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
                transcription_labels.transcript,
                transcription_labels.status,
                transcription_labels.unsure,
                transcription_labels.notes,
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


def export_labels_csv(all_rows: bool = False) -> Response:
    rows = read_label_items(limit=100000)
    if not all_rows:
        rows = [
            row
            for row in rows
            if row["status"] == "labeled" and not row["unsure"] and row["transcript"].strip()
        ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    filename = "transcription-labels-all.csv" if all_rows else "training-labels.csv"
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
