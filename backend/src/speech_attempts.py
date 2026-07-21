from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import Response

from .database import connect_db
from .text import normalize_text

SPEECH_ATTEMPT_FIELDS = [
    "created_at",
    "audio_id",
    "audio_file",
    "raw_transcript",
    "target_text",
    "selected_candidate_id",
    "selected_candidate_source",
    "suggested_candidate_id",
    "suggested_text",
    "suggestion_score",
]


def read_speech_attempts(limit: int | None = None) -> list[dict]:
    query = """
        SELECT
            speech_attempts.created_at,
            speech_attempts.audio_id,
            audio_samples.file_path AS audio_file,
            speech_attempts.raw_transcript,
            speech_attempts.target_text,
            speech_attempts.selected_candidate_id,
            speech_attempts.selected_candidate_source,
            speech_attempts.suggested_candidate_id,
            speech_attempts.suggested_text,
            speech_attempts.suggestion_score
        FROM speech_attempts
        JOIN audio_samples ON audio_samples.id = speech_attempts.audio_id
        ORDER BY speech_attempts.created_at DESC, speech_attempts.id DESC
    """
    if limit:
        query += " LIMIT ?"
        args = (limit,)
    else:
        args = ()
    with connect_db() as db:
        rows = db.execute(query, args).fetchall()
    return [dict(row) for row in rows]


def create_speech_attempt(
    audio_id: str,
    raw_transcript: str,
    target_text: str,
    selected_candidate_id: str,
    selected_candidate_source: str,
    suggested_candidate_id: str,
    suggested_text: str,
    suggestion_score: str,
) -> dict:
    if not target_text.strip():
        raise HTTPException(status_code=400, detail="Target text is required.")

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        parsed_score = float(suggestion_score) if suggestion_score else None
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid speech attempt metadata.") from error
    with connect_db() as db:
        audio = db.execute("SELECT id FROM audio_samples WHERE id = ?", (audio_id,)).fetchone()
        if not audio:
            raise HTTPException(status_code=404, detail="Audio sample not found.")
        cursor = db.execute(
            """
            INSERT INTO speech_attempts (
                audio_id,
                raw_transcript,
                target_text,
                selected_candidate_id,
                selected_candidate_source,
                suggested_candidate_id,
                suggested_text,
                suggestion_score,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_id,
                raw_transcript,
                target_text,
                selected_candidate_id,
                selected_candidate_source,
                suggested_candidate_id,
                suggested_text,
                parsed_score,
                created_at,
            ),
        )
    return {"id": cursor.lastrowid, "ok": True}


def export_speech_attempts_csv() -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=SPEECH_ATTEMPT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(read_speech_attempts())
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=speech-attempts.csv"},
    )


def analyze_speech_attempts() -> dict:
    records = read_speech_attempts()
    total = len(records)
    exact = sum(
        1
        for row in records
        if normalize_text(row.get("raw_transcript", ""))
        == normalize_text(row.get("target_text", ""))
    )
    top_1 = sum(
        1
        for row in records
        if row.get("selected_candidate_id")
        and row.get("selected_candidate_id") == row.get("suggested_candidate_id")
    )
    return {
        "total": total,
        "exact_matches": exact,
        "exact_match_rate": exact / total if total else 0,
        "top_1_matches": top_1,
        "top_1_rate": top_1 / total if total else 0,
    }
