from pathlib import Path

from fastapi.testclient import TestClient

from src import database
from src.app import create_app
from src.database import connect_db
from src.routers import training
from src.tatoeba import ensure_prompts, write_prompts


def test_training_prompts_come_from_cached_tatoeba(initialized_db: Path, monkeypatch) -> None:
    prompts_file = initialized_db / "tatoeba.json"
    monkeypatch.setattr(training, "TATOEBA_PROMPTS_FILE", prompts_file)
    write_prompts(prompts_file, [{"id": "123", "text": "Das ist ein ausreichend langer deutscher Beispielsatz."}])
    client = TestClient(create_app())

    response = client.get("/api/training/prompts")

    assert response.status_code == 200
    assert response.json()["prompts"] == [{"id": "tatoeba:123", "text": "Das ist ein ausreichend langer deutscher Beispielsatz."}]


def test_guided_recording_saves_known_prompt_as_training_ready(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    prompts_file = initialized_db / "tatoeba.json"
    monkeypatch.setattr(training, "TATOEBA_PROMPTS_FILE", prompts_file)
    monkeypatch.setattr(training, "transcribe_german", lambda audio_path: "Das ist ein Beispielsatz")
    write_prompts(prompts_file, [{"id": "123", "text": "Das ist ein ausreichend langer deutscher Beispielsatz."}])
    client = TestClient(create_app())
    prompt = client.get("/api/training/prompts").json()["prompts"][0]

    response = client.post(
        "/api/training/recordings",
        data={"prompt_id": prompt["id"]},
        files={"audio": ("reading.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["source"] == "training_reading"
    assert item["transcript"] == prompt["text"]
    assert item["status"] == "labeled"
    assert item["unsure"] is False
    assert (initialized_db / item["audio_file"]).read_bytes() == b"audio bytes"
    with connect_db() as db:
        assert db.execute("SELECT COUNT(*) FROM audio_clips").fetchone()[0] == 1
        assert db.execute(
            "SELECT asr_text FROM transcription_labels WHERE audio_id = ?", (item["audio_id"],)
        ).fetchone()["asr_text"] == "Das ist ein Beispielsatz"


def test_guided_recording_rejects_unknown_prompt(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    response = TestClient(create_app()).post(
        "/api/training/recordings",
        data={"prompt_id": "not-a-prompt"},
        files={"audio": ("reading.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 400


def test_tatoeba_recording_uses_the_cached_known_text(initialized_db: Path, monkeypatch) -> None:
    prompts_file = initialized_db / "tatoeba.json"
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(training, "TATOEBA_PROMPTS_FILE", prompts_file)
    monkeypatch.setattr(training, "transcribe_german", lambda audio_path: "Das ist ein Beispielsatz")
    write_prompts(prompts_file, [{"id": "123", "text": "Das ist ein ausreichend langer deutscher Beispielsatz."}])
    client = TestClient(create_app())

    prompts = client.get("/api/training/prompts")
    recording = client.post(
        "/api/training/recordings",
        data={"prompt_id": "tatoeba:123"},
        files={"audio": ("reading.webm", b"audio bytes", "audio/webm")},
    )

    assert prompts.json()["prompts"][0]["id"] == "tatoeba:123"
    assert recording.json()["item"]["transcript"] == "Das ist ein ausreichend langer deutscher Beispielsatz."


def test_guided_recording_saves_when_asr_is_unavailable(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    prompts_file = initialized_db / "tatoeba.json"
    monkeypatch.setattr(training, "TATOEBA_PROMPTS_FILE", prompts_file)
    monkeypatch.setattr(training, "transcribe_german", lambda audio_path: (_ for _ in ()).throw(RuntimeError()))
    write_prompts(prompts_file, [{"id": "123", "text": "Das ist ein Beispielsatz."}])

    response = TestClient(create_app()).post(
        "/api/training/recordings",
        data={"prompt_id": "tatoeba:123"},
        files={"audio": ("reading.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["item"]["asr_text"] == ""


def test_tatoeba_cache_is_not_downloaded_when_it_exists(tmp_path: Path, monkeypatch) -> None:
    prompts_file = tmp_path / "tatoeba.json"
    write_prompts(prompts_file, [{"id": "123", "text": "Ein vorhandener Beispielsatz bleibt erhalten."}])
    monkeypatch.setattr(
        "src.tatoeba.download_prompts",
        lambda: (_ for _ in ()).throw(AssertionError("Download must not run")),
    )

    assert ensure_prompts(prompts_file) == 1


def test_existing_database_is_upgraded_for_guided_reading(initialized_db: Path) -> None:
    with connect_db() as db:
        db.commit()
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DROP TABLE audio_clips")
        db.execute(
            """
            CREATE TABLE audio_clips (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL DEFAULT '',
                content_type TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL CHECK (source IN ('app_recording', 'whatsapp_upload')),
                created_at TEXT NOT NULL
            )
            """
        )
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")

    database.init_db()

    with connect_db() as db:
        schema = db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'audio_clips'"
        ).fetchone()["sql"]
    assert "training_reading" in schema
