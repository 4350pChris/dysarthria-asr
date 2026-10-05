from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

from fastapi.testclient import TestClient

from src import transcript_review
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
        assert payload["temperature"] == 0
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["provider"] == {"data_collection": "deny"}
        assert request.get_header("Authorization") == "Bearer test-key"
        assert request.full_url.endswith("/chat/completions")
        assert timeout == 45
        return BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps({"suggestions": suggestions})}}]}).encode())

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(transcript_review, "urlopen", reply)
    assert transcript_review.review_transcript(text).model_dump() == {
        "suggestions": [{"original": "Brot bewohnen", "replacement": "Probewohnen"}]
    }


def test_review_errors_do_not_claim_that_the_text_is_correct(initialized_db: Path, monkeypatch) -> None:
    from src.app import create_app

    client = TestClient(create_app())
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert client.post("/api/transcript/review", json={"text": "Hallo"}).status_code == 503
    monkeypatch.setattr(transcription, "review_transcript", lambda text: (_ for _ in ()).throw(URLError("offline")))
    assert client.post("/api/transcript/review", json={"text": "Hallo"}).status_code == 503
    monkeypatch.setattr(transcript_review, "urlopen", lambda *args, **kwargs: BytesIO(b'{"choices": []}'))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(transcription, "review_transcript", transcript_review.review_transcript)
    assert client.post("/api/transcript/review", json={"text": "Hallo"}).status_code == 502
    for text in ("", " ", "a" * 6_001):
        assert client.post("/api/transcript/review", json={"text": text}).status_code == 422
