from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import Response

from ..corrections import (
    analyze_corrections,
    export_corrections_csv,
    read_corrections,
    save_correction,
)

router = APIRouter(prefix="/api")


@router.post("/corrections")
async def create_correction(
    audio_id: str = Form(...),
    audio_path: str = Form(""),
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
    return save_correction(
        audio_id=audio_id,
        audio_path=audio_path,
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


@router.get("/corrections")
def list_corrections() -> list[dict]:
    return read_corrections()[-50:][::-1]


@router.get("/corrections.csv")
def export_corrections() -> Response:
    return export_corrections_csv()


@router.get("/analysis")
def analyze() -> dict:
    return analyze_corrections()
