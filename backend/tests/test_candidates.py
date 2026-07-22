from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from src.candidates import candidate_suggestions, read_candidates, read_generated_candidates
from src.corpus import create_audio_clip, label_counts, read_label_items, upsert_transcription_label
from src.database import init_db
from src.phrases import create_phrase, read_categories


def test_generated_candidates_rank_and_labels_save_provisional_transcript(initialized_db: Path) -> None:
    generated = read_generated_candidates()
    assert any(item["text"] == "Ich möchte Kaffee." for item in generated)
    assert any(item["text"] == "Wo ist meine Brille?" for item in generated)
    assert any(item["text"] == "Ich muss zur Toilette." for item in generated)
    assert any(item["text"] == "Mir ist kalt." for item in generated)
    assert any(item["text"] == "Ich habe Schmerzen am Kopf." for item in generated)
    assert any(item["text"] == "Ich habe Schmerzen in der Hand." for item in generated)
    assert any(item["text"] == "Mein Bauch tut weh." for item in generated)
    assert any(item["text"] == "Meine Hand tut weh." for item in generated)
    assert any(item["text"] == "Hilf mir bitte beim Aufstehen." for item in generated)
    assert not any(item["text"] == "Hilf mir bitte beim raus." for item in generated)
    assert not any(item["text"] == "Wo ist meine Medikamente?" for item in generated)
    assert not any(item["text"] == "Mir geht es zu laut." for item in generated)
    assert not any(item["text"] == "Ich habe Schmerzen in der Kopf." for item in generated)
    assert not any(item["text"] == "Ich habe Schmerzen am Hand." for item in generated)
    assert not any(item["text"] == "Meine Bauch tut weh." for item in generated)
    assert not any(item["text"] == "Mein Hand tut weh." for item in generated)
    assert not any(item["text"] == "Ich möchte jetzt." for item in generated)
    assert not any(item["text"] == "Ich brauche kurz später." for item in generated)
    assert len(generated) < 250

    suggestions = candidate_suggestions("ich möchte kaffee")
    assert len(suggestions) >= 5
    assert suggestions[0]["id"]

    audio_id = uuid4().hex
    create_audio_clip(audio_id, "data/audio/test.webm", "test.webm", "audio/webm", "app_recording")
    upsert_transcription_label(
        audio_id=audio_id,
        asr_text="ich möchte kaffee",
        transcript="Ich möchte Kaffee.",
    )

    labels = read_label_items()
    assert labels[0]["audio_id"] == audio_id
    assert labels[0]["transcript"] == "Ich möchte Kaffee."
    assert labels[0]["status"] == "draft"


def test_label_counts_track_status(initialized_db: Path) -> None:
    audio_id = uuid4().hex
    create_audio_clip(audio_id, "data/audio/test.webm", "test.webm", "audio/webm", "app_recording")
    upsert_transcription_label(
        audio_id=audio_id,
        asr_text="Ich möchte Kaffee.",
        transcript="ich möchte kaffee",
        status="labeled",
    )

    assert label_counts() == {
        "total": 1,
        "draft": 0,
        "labeled": 1,
        "skipped": 0,
    }


def test_init_db_preserves_existing_labels_and_seed_rows(initialized_db: Path) -> None:
    category_count = len(read_categories())
    generated_count = len(read_generated_candidates())
    audio_id = uuid4().hex
    create_audio_clip(audio_id, "data/audio/test.webm", "test.webm", "audio/webm", "app_recording")
    upsert_transcription_label(
        audio_id=audio_id,
        asr_text="Ich möchte Kaffee.",
        transcript="Ich möchte Kaffee.",
    )

    init_db()

    assert read_label_items()[0]["audio_id"] == audio_id
    assert len(read_categories()) == category_count
    assert len(read_generated_candidates()) == generated_count


def test_init_db_drops_legacy_attempt_tables(initialized_db: Path) -> None:
    from src.database import connect_db

    with connect_db() as db:
        db.execute("CREATE TABLE speech_attempts (id INTEGER PRIMARY KEY)")
        db.execute("CREATE TABLE audio_samples (id TEXT PRIMARY KEY)")

    init_db()

    with connect_db() as db:
        legacy = db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name IN ('speech_attempts', 'audio_samples')
            """
        ).fetchall()

    assert legacy == []


def test_read_candidates_deduplicates_generated_text_when_phrase_exists(initialized_db: Path) -> None:
    category = read_categories()[0]
    create_phrase(category["id"], "Ich möchte Kaffee.")

    matches = [item for item in read_candidates() if item["text"] == "Ich möchte Kaffee."]

    assert len(matches) == 1
    assert matches[0]["source"] == "phrase"


def test_generated_candidates_endpoint(initialized_db: Path) -> None:
    from src.app import create_app

    response = TestClient(create_app()).get("/api/candidates/generated")

    assert response.status_code == 200
    assert any(item["text"] == "Ich möchte Kaffee." for item in response.json())
