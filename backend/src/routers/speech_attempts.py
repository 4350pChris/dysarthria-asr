from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import Response

from ..speech_attempts import (
    analyze_speech_attempts,
    create_speech_attempt,
    export_speech_attempts_csv,
    read_speech_attempts,
)

router = APIRouter(prefix="/api")


@router.post("/speech-attempts")
async def add_speech_attempt(
    audio_id: str = Form(...),
    source: str = Form("browser_recording"),
    phrase_id: str = Form(""),
    expected_text: str = Form(""),
    raw_transcript: str = Form(""),
    corrected_text: str = Form(...),
    suggested_phrase_id: str = Form(""),
    suggested_text: str = Form(""),
    suggestion_score: str = Form(""),
    was_understandable: bool = Form(False),
    notes: str = Form(""),
) -> dict:
    return create_speech_attempt(
        audio_id=audio_id,
        source=source,
        phrase_id=phrase_id,
        expected_text=expected_text,
        raw_transcript=raw_transcript,
        corrected_text=corrected_text,
        suggested_phrase_id=suggested_phrase_id,
        suggested_text=suggested_text,
        suggestion_score=suggestion_score,
        was_understandable=was_understandable,
        notes=notes,
    )


@router.get("/speech-attempts")
def list_speech_attempts() -> list[dict]:
    return read_speech_attempts(limit=50)


@router.get("/speech-attempts.csv")
def export_speech_attempts() -> Response:
    return export_speech_attempts_csv()


@router.get("/analysis")
def analyze() -> dict:
    return analyze_speech_attempts()
