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
    raw_transcript: str = Form(""),
    target_text: str = Form(...),
    selected_candidate_id: str = Form(""),
    selected_candidate_source: str = Form(""),
    suggested_candidate_id: str = Form(""),
    suggested_text: str = Form(""),
    suggestion_score: str = Form(""),
) -> dict:
    return create_speech_attempt(
        audio_id=audio_id,
        raw_transcript=raw_transcript,
        target_text=target_text,
        selected_candidate_id=selected_candidate_id,
        selected_candidate_source=selected_candidate_source,
        suggested_candidate_id=suggested_candidate_id,
        suggested_text=suggested_text,
        suggestion_score=suggestion_score,
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
