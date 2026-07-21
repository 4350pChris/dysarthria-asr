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
    "source",
    "phrase_id",
    "expected_text",
    "raw_transcript",
    "corrected_text",
    "suggested_phrase_id",
    "suggested_text",
    "suggestion_score",
    "was_understandable",
    "notes",
]


def read_speech_attempts(limit: int | None = None) -> list[dict]:
    query = """
        SELECT
            speech_attempts.created_at,
            speech_attempts.audio_id,
            audio_samples.file_path AS audio_file,
            speech_attempts.source,
            speech_attempts.phrase_id,
            speech_attempts.expected_text,
            speech_attempts.raw_transcript,
            speech_attempts.corrected_text,
            speech_attempts.suggested_phrase_id,
            speech_attempts.suggested_text,
            speech_attempts.suggestion_score,
            speech_attempts.was_understandable,
            speech_attempts.notes
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
    return [
        {
            **dict(row),
            "was_understandable": bool(row["was_understandable"]),
        }
        for row in rows
    ]


def create_speech_attempt(
    audio_id: str,
    source: str,
    phrase_id: str,
    expected_text: str,
    raw_transcript: str,
    corrected_text: str,
    suggested_phrase_id: str,
    suggested_text: str,
    suggestion_score: str,
    was_understandable: bool,
    notes: str,
) -> dict:
    if not corrected_text.strip():
        raise HTTPException(status_code=400, detail="Corrected text is required.")

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        parsed_phrase_id = int(phrase_id) if phrase_id else None
        parsed_suggested_phrase_id = int(suggested_phrase_id) if suggested_phrase_id else None
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
                source,
                phrase_id,
                expected_text,
                raw_transcript,
                corrected_text,
                suggested_phrase_id,
                suggested_text,
                suggestion_score,
                was_understandable,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_id,
                source,
                parsed_phrase_id,
                expected_text,
                raw_transcript,
                corrected_text,
                parsed_suggested_phrase_id,
                suggested_text,
                parsed_score,
                int(was_understandable),
                notes,
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
    understandable = sum(1 for row in records if row.get("was_understandable"))
    exact = sum(
        1
        for row in records
        if normalize_text(row.get("raw_transcript", ""))
        == normalize_text(row.get("expected_text", ""))
    )
    fuzzy_top_1 = sum(
        1
        for row in records
        if row.get("phrase_id")
        and row.get("phrase_id") == row.get("suggested_phrase_id")
    )
    by_phrase = {}
    for row in records:
        key = row.get("phrase_id") or "?"
        item = by_phrase.setdefault(
            key,
            {"phrase_id": key, "expected_text": row.get("expected_text", ""), "attempts": 0, "failures": 0},
        )
        item["attempts"] += 1
        if not row.get("was_understandable"):
            item["failures"] += 1
    worst_phrases = sorted(
        by_phrase.values(),
        key=lambda item: (-item["failures"], -item["attempts"], str(item["phrase_id"])),
    )[:10]
    return {
        "total": total,
        "understandable": understandable,
        "understandable_rate": understandable / total if total else 0,
        "exact_matches": exact,
        "exact_match_rate": exact / total if total else 0,
        "fuzzy_top_1_matches": fuzzy_top_1,
        "fuzzy_top_1_rate": fuzzy_top_1 / total if total else 0,
        "worst_phrases": worst_phrases,
    }
