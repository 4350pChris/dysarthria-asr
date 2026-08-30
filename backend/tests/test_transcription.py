from __future__ import annotations

from pathlib import Path

from conftest import connect_test_db, change_label, make_audio_clip
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
    assert body["emoji_text"] == "ich möchte kaffee"
    assert body["audio_path"].startswith("audio/")
    assert body["suggestions"][0]["text"] == "Ich möchte Kaffee."

    with connect_test_db(database.DB_FILE) as db:
        audio = db.execute("SELECT file_path, content_type, source FROM audio_clips").fetchone()
        label = db.execute(
            "SELECT asr_text, asr_source, transcript, status FROM transcription_labels"
        ).fetchone()
    assert dict(audio) == {
        "file_path": body["audio_path"],
        "content_type": "audio/webm",
        "source": "app_recording",
    }
    assert dict(label) == {
        "asr_text": "ich möchte kaffee",
        "asr_source": "server",
        "transcript": "",
        "status": "draft",
    }


def test_transcribe_returns_converted_emoji_text(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(transcription, "ROOT", initialized_db)
    monkeypatch.setattr(transcription, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(transcription, "transcribe_german", lambda audio_path: "weißes Herz emoji")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/transcribe",
        files={"audio": ("sample.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["emoji_text"] == "🤍"


def test_transcribe_returns_a_spoken_emoji_name(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(transcription, "ROOT", initialized_db)
    monkeypatch.setattr(transcription, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(transcription, "transcribe_german", lambda audio_path: "weißes Herz")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/transcribe",
        files={"audio": ("sample.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["emoji_value"] == "🤍"
    assert body["emoji_name"] == "weißes Herz"


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


def test_partial_transcription_returns_text_without_saving_audio_or_label(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(transcription, "ROOT", initialized_db)
    monkeypatch.setattr(transcription, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(transcription, "transcribe_german", lambda audio_path: "ich möchte kaffee")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/transcribe/partial",
        files={"audio": ("recording.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"raw_transcript": "ich möchte kaffee"}
    with connect_test_db(database.DB_FILE) as db:
        assert db.execute("SELECT COUNT(*) FROM audio_clips").fetchone()[0] == 0
    assert not list((initialized_db / "audio").glob("*"))


def test_recent_emojis_returns_saved_recognized_emojis(
    initialized_db: Path,
    session,
) -> None:
    make_audio_clip(session, "older", "data/audio/older.webm", source="app_recording")
    change_label(session, "older", asr_text="weißes Herz", transcript="kein Emoji")
    make_audio_clip(session, "newer", "data/audio/newer.webm", source="app_recording")
    change_label(session, "newer", transcript="Daumen hoch")

    from src.app import create_app

    response = TestClient(create_app()).get("/api/emojis/recent")

    assert response.status_code == 200
    assert response.json() == [
        {"value": "👍", "name": "Daumen hoch"},
        {"value": "🤍", "name": "weißes Herz"},
    ]


def test_transcribe_does_not_store_audio_without_asr_text(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(transcription, "ROOT", initialized_db)
    monkeypatch.setattr(transcription, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(transcription, "transcribe_german", lambda audio_path: "  ")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/transcribe",
        files={"audio": ("sample.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Keine Sprache erkannt."
    with connect_test_db(database.DB_FILE) as db:
        assert db.execute("SELECT COUNT(*) FROM audio_clips").fetchone()[0] == 0
    assert not list((initialized_db / "audio").glob("*.webm"))
