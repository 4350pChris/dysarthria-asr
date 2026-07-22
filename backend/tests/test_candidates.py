from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from src.audio_samples import create_audio_sample
from src.candidates import candidate_suggestions, read_candidates, read_generated_candidates
from src.phrases import create_phrase, read_categories
from src.speech_attempts import analyze_speech_attempts, create_speech_attempt, read_speech_attempts


def test_generated_candidates_rank_and_attempts_save_training_label(initialized_db: Path) -> None:
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
    create_audio_sample(audio_id, "data/audio/test.webm", "audio/webm")
    create_speech_attempt(
        audio_id=audio_id,
        raw_transcript="ich möchte kaffee",
        target_text="Ich möchte Kaffee.",
        selected_candidate_id=suggestions[0]["id"],
        selected_candidate_source=suggestions[0]["source"],
        suggested_candidate_id=suggestions[0]["id"],
        suggested_text=suggestions[0]["text"],
        suggestion_score=str(suggestions[0]["score"]),
    )

    attempts = read_speech_attempts()
    assert attempts[0]["audio_id"] == audio_id
    assert attempts[0]["target_text"] == "Ich möchte Kaffee."


def test_speech_attempt_analysis_tracks_exact_and_top_candidate(initialized_db: Path) -> None:
    audio_id = uuid4().hex
    create_audio_sample(audio_id, "data/audio/test.webm", "audio/webm")
    create_speech_attempt(
        audio_id=audio_id,
        raw_transcript="Ich möchte Kaffee.",
        target_text="ich möchte kaffee",
        selected_candidate_id="generated:1:2",
        selected_candidate_source="generated",
        suggested_candidate_id="generated:1:2",
        suggested_text="Ich möchte Kaffee.",
        suggestion_score="0.98",
    )

    analysis = analyze_speech_attempts()
    assert analysis == {
        "total": 1,
        "exact_matches": 1,
        "exact_match_rate": 1,
        "top_1_matches": 1,
        "top_1_rate": 1,
    }


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
