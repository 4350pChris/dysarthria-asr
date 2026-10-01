from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

from conftest import connect_test_db
from fastapi.testclient import TestClient

from src import database, transcript_review
from src.routers import transcription


def test_review_keeps_only_unique_non_overlapping_changes(monkeypatch) -> None:
    text = "🤍 Ich hatte mein Brot bewohnen. Hallo Hallo."
    suggestions = [
        {"original": "Brot bewohnen", "replacement": "Probewohnen"},
        {"original": "mein Brot", "replacement": "mein Probe"},
        {"original": "Hallo", "replacement": "Guten Tag"},
        {"original": "fehlt", "replacement": "Wort"},
        {"original": "Ich", "replacement": "Ich"},
    ]
    def reply(request, timeout):
        payload = json.loads(request.data)
        assert payload["messages"][1]["content"] == text
        assert payload["stream"] is False
        assert payload["options"]["num_thread"] == 4
        assert payload["think"] is False
        assert request.full_url.endswith("/api/chat")
        assert timeout == 45
        return BytesIO(json.dumps({"message": {"content": json.dumps({"suggestions": suggestions})}}).encode())

    monkeypatch.setattr(transcript_review, "urlopen", reply)
    assert transcript_review.review_transcript(text).model_dump() == {
        "suggestions": [{"original": "Brot bewohnen", "replacement": "Probewohnen"}]
    }


def test_review_errors_do_not_claim_that_the_text_is_correct(initialized_db: Path, monkeypatch) -> None:
    from src.app import create_app

    client = TestClient(create_app())
    monkeypatch.setattr(transcription, "review_transcript", lambda text: (_ for _ in ()).throw(URLError("offline")))
    assert client.post("/api/transcript/review", json={"text": "Hallo"}).status_code == 503
    monkeypatch.setattr(transcript_review, "urlopen", lambda *args, **kwargs: BytesIO(b'{"choices": []}'))
    monkeypatch.setattr(transcription, "review_transcript", transcript_review.review_transcript)
    assert client.post("/api/transcript/review", json={"text": "Hallo"}).status_code == 502
    for text in ("", " ", "a" * 6_001):
        assert client.post("/api/transcript/review", json={"text": text}).status_code == 422


def test_replacement_audio_is_temporary_and_does_not_create_labels(initialized_db: Path, monkeypatch) -> None:
    from src.app import create_app

    paths: list[Path] = []
    def recognize(path):
        paths.append(path)
        assert path.read_bytes() == b"replacement audio"
        return "Probewohnen"

    monkeypatch.setattr(transcription, "transcribe_german", recognize)
    client = TestClient(create_app())
    response = client.post("/api/transcribe/replacement", files={"audio": ("part.webm", b"replacement audio", "audio/webm")})
    assert response.json() == {"text": "Probewohnen"}
    assert not paths[0].exists()
    with connect_test_db(database.DB_FILE) as db:
        assert db.execute("SELECT COUNT(*) FROM audio_clips").fetchone()[0] == 0
    monkeypatch.setattr(transcription, "transcribe_german", lambda path: " ")
    assert client.post("/api/transcribe/replacement", files={"audio": ("part.webm", b"audio")}).status_code == 422
    assert client.post("/api/transcribe/replacement", files={"audio": ("part.webm", b"")}).status_code == 400
    assert client.post("/api/transcribe/replacement", files={"audio": ("part.webm", b"x" * (10 * 1024 * 1024 + 1))}).status_code == 413
