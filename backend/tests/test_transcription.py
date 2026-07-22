from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src import database
from src.routers import transcription


def test_transcribe_saves_audio_and_returns_candidate_suggestions(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(transcription, "ROOT", initialized_db)
    monkeypatch.setattr(transcription, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(transcription, "transcribe_german", lambda audio_path: "ich möchte kaffee")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/transcribe",
        files={"audio": ("sample.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["raw_transcript"] == "ich möchte kaffee"
    assert body["audio_path"].startswith("audio/")
    assert body["suggestions"][0]["text"] == "Ich möchte Kaffee."

    with database.connect_db() as db:
        audio = db.execute("SELECT file_path, content_type, source FROM audio_clips").fetchone()
        label = db.execute("SELECT asr_text, transcript, status FROM transcription_labels").fetchone()
    assert dict(audio) == {
        "file_path": body["audio_path"],
        "content_type": "audio/webm",
        "source": "app_recording",
    }
    assert dict(label) == {
        "asr_text": "ich möchte kaffee",
        "transcript": "",
        "status": "draft",
    }


def test_transcribe_rejects_empty_audio(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(transcription, "ROOT", initialized_db)
    monkeypatch.setattr(transcription, "AUDIO_DIR", initialized_db / "audio")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/transcribe",
        files={"audio": ("empty.webm", b"", "audio/webm")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload a non-empty audio file."
