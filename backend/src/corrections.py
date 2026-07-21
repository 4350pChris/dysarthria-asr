from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

from fastapi.responses import Response

from .paths import CORRECTIONS_FILE, DATA_DIR
from .text import normalize_text

CORRECTION_FIELDS = [
    "created_at",
    "audio_id",
    "audio_file",
    "source",
    "phrase_number",
    "expected_text",
    "raw_transcript",
    "corrected_text",
    "suggested_phrase_number",
    "suggested_text",
    "suggestion_score",
    "was_understandable",
    "notes",
]


def read_corrections() -> list[dict]:
    if not CORRECTIONS_FILE.exists():
        return []
    return [
        json.loads(line)
        for line in CORRECTIONS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def save_correction(
    audio_id: str,
    audio_path: str,
    source: str,
    phrase_number: str,
    expected_text: str,
    raw_transcript: str,
    corrected_text: str,
    suggested_phrase_number: str,
    suggested_text: str,
    suggestion_score: str,
    was_understandable: bool,
    notes: str,
) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio_id": audio_id,
        "audio_file": audio_path,
        "source": source,
        "phrase_number": phrase_number,
        "expected_text": expected_text,
        "raw_transcript": raw_transcript,
        "corrected_text": corrected_text,
        "suggested_phrase_number": suggested_phrase_number,
        "suggested_text": suggested_text,
        "suggestion_score": suggestion_score,
        "was_understandable": was_understandable,
        "notes": notes,
    }
    with CORRECTIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


def export_corrections_csv() -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CORRECTION_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(read_corrections())
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=corrections.csv"},
    )


def analyze_corrections() -> dict:
    records = read_corrections()
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
        if row.get("phrase_number")
        and row.get("phrase_number") == row.get("suggested_phrase_number")
    )
    by_phrase = {}
    for row in records:
        key = row.get("phrase_number") or "?"
        item = by_phrase.setdefault(
            key,
            {"phrase_number": key, "expected_text": row.get("expected_text", ""), "attempts": 0, "failures": 0},
        )
        item["attempts"] += 1
        if not row.get("was_understandable"):
            item["failures"] += 1
    worst_phrases = sorted(
        by_phrase.values(),
        key=lambda item: (-item["failures"], -item["attempts"], item["phrase_number"]),
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
