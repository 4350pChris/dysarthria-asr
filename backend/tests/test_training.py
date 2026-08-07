from pathlib import Path

from fastapi.testclient import TestClient

from src import database
from src.app import create_app
from src.database import connect_db
from src.routers import training


def test_training_prompts_are_grouped_by_topic() -> None:
    client = TestClient(create_app())

    topics = client.get("/api/training/topics").json()["topics"]
    response = client.get("/api/training/prompts", params={"topic": topics[0]})

    assert response.status_code == 200
    assert response.json()["prompts"]
    assert {prompt["topic"] for prompt in response.json()["prompts"]} == {topics[0]}


def test_guided_recording_saves_known_prompt_as_training_ready(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    client = TestClient(create_app())
    prompt = client.get("/api/training/prompts", params={"topic": "Alltag"}).json()["prompts"][0]

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


def test_guided_recording_rejects_unknown_prompt(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    response = TestClient(create_app()).post(
        "/api/training/recordings",
        data={"prompt_id": "not-a-prompt"},
        files={"audio": ("reading.webm", b"audio bytes", "audio/webm")},
    )

    assert response.status_code == 400


def test_tatoeba_import_and_recording_use_the_cached_known_text(initialized_db: Path, monkeypatch) -> None:
    prompts_file = initialized_db / "tatoeba.json"
    monkeypatch.setattr(training, "ROOT", initialized_db)
    monkeypatch.setattr(training, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(training, "TATOEBA_PROMPTS_FILE", prompts_file)
    monkeypatch.setattr(training, "download_prompts", lambda: [{"id": "123", "text": "Das ist ein ausreichend langer deutscher Beispielsatz."}])
    client = TestClient(create_app())

    imported = client.post("/api/training/tatoeba/import")
    prompts = client.get("/api/training/prompts", params={"topic": "Tatoeba CC0"})
    recording = client.post(
        "/api/training/recordings",
        data={"prompt_id": "tatoeba:123"},
        files={"audio": ("reading.webm", b"audio bytes", "audio/webm")},
    )

    assert imported.json()["imported"] == 1
    assert prompts.json()["prompts"][0]["source"] == "Tatoeba CC0"
    assert recording.json()["item"]["transcript"] == "Das ist ein ausreichend langer deutscher Beispielsatz."


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
