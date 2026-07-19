from __future__ import annotations

import json
import os
import uuid
import csv
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .asr import transcribe_german

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
CORRECTIONS_FILE = DATA_DIR / "corrections.jsonl"
PHRASES_FILE = DATA_DIR / "phrases.csv"

app = FastAPI(title="Dysarthria ASR Prototype")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
    if not CORRECTIONS_FILE.exists():
        return []
    records = [
        json.loads(line)
        for line in CORRECTIONS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return records[-50:][::-1]


@app.get("/api/phrases")
def list_phrases() -> list[dict]:
    if not PHRASES_FILE.exists():
        return []
    with PHRASES_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if os.getenv("DYSARTHRIA_ASR_DEV"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
