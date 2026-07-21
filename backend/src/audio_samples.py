from __future__ import annotations

from datetime import datetime, timezone

from .database import connect_db


def create_audio_sample(
    id: str,
    file_path: str,
    content_type: str = "",
) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as db:
        db.execute(
            """
            INSERT INTO audio_samples (id, file_path, content_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (id, file_path, content_type, created_at),
        )
    return {
        "id": id,
        "file_path": file_path,
        "content_type": content_type,
        "created_at": created_at,
    }
