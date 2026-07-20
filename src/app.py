from __future__ import annotations

import json
import os
import uuid
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .asr import transcribe_german

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
CORRECTIONS_FILE = DATA_DIR / "corrections.jsonl"
PHRASES_FILE = DATA_DIR / "phrases.csv"
CORRECTION_FIELDS = [
    "created_at",
    "audio_id",
    "audio_file",
    "source",
    "phrase_number",
    "expected_text",
    "raw_transcript",
    "corrected_text",
    "was_understandable",
    "notes",
]

app = FastAPI(title="Dysarthria ASR Prototype")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def read_corrections() -> list[dict]:
    if not CORRECTIONS_FILE.exists():
        return []
    return [
        json.loads(line)
        for line in CORRECTIONS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalize_text(text: str) -> str:
    return " ".join(text.casefold().strip().rstrip(".!?").split())


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix or ".webm"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty audio file.")
    audio_path.write_bytes(contents)

    transcript = transcribe_german(audio_path)
    return {
        "audio_id": audio_id,
        "audio_path": str(audio_path.relative_to(ROOT)),
        "raw_transcript": transcript,
    }


@app.post("/api/corrections")
async def save_correction(
    audio_id: str = Form(...),
    audio_path: str = Form(""),
    source: str = Form("browser_recording"),
    phrase_number: str = Form(""),
    expected_text: str = Form(""),
    raw_transcript: str = Form(""),
    corrected_text: str = Form(...),
    was_understandable: bool = Form(False),
    notes: str = Form(""),
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
        "was_understandable": was_understandable,
        "notes": notes,
    }
    with CORRECTIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


@app.get("/api/corrections")
def list_corrections() -> list[dict]:
    return read_corrections()[-50:][::-1]


@app.get("/api/corrections.csv")
def export_corrections() -> Response:
    records = read_corrections()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CORRECTION_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=corrections.csv"},
    )


@app.get("/api/analysis")
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
        "worst_phrases": worst_phrases,
    }


@app.get("/api/phrases")
def list_phrases() -> list[dict]:
    if not PHRASES_FILE.exists():
        return []
    with PHRASES_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if os.getenv("DYSARTHRIA_ASR_DEV"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
