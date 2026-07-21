from __future__ import annotations

from datetime import datetime, timezone

from .database import connect_db


def create_audio_sample(
    id: str,
    file_path: str,
    original_filename: str = "",
    content_type: str = "",
) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as db:
        db.execute(
            """
            INSERT INTO audio_samples (id, file_path, original_filename, content_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (id, file_path, original_filename, content_type, created_at),
        )
    return {
        "id": id,
        "file_path": file_path,
        "original_filename": original_filename,
        "content_type": content_type,
        "created_at": created_at,
    }
