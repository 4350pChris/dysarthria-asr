from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app
from src.candidates import read_generated_candidates


def test_grammar_endpoint_updates_generated_candidates(initialized_db: Path) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    value = next(item for item in thing_slot["values"] if item["value"] == "Kaffee")

    response = client.patch(
        f"/api/grammar/values/{value['id']}",
        data={"value": "Kakao"},
    )

    assert response.status_code == 200
    generated_texts = {item["text"] for item in read_generated_candidates()}
    assert "Ich möchte Kakao." in generated_texts
    assert "Ich möchte Kaffee." not in generated_texts


def test_grammar_endpoint_updates_pattern_templates(initialized_db: Path) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    pattern = next(item for item in thing_slot["patterns"] if item["template"] == "Ich möchte {thing_acc}.")

    response = client.patch(
        f"/api/grammar/patterns/{pattern['id']}",
        data={"template": "Bitte bring mir {thing_acc}."},
    )

    assert response.status_code == 200
    generated_texts = {item["text"] for item in read_generated_candidates()}
    assert "Bitte bring mir Kaffee." in generated_texts
    assert "Ich möchte Kaffee." not in generated_texts


def test_grammar_pattern_requires_its_placeholder(initialized_db: Path) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    pattern = next(item for item in thing_slot["patterns"] if item["template"] == "Ich möchte {thing_acc}.")

    response = client.patch(
        f"/api/grammar/patterns/{pattern['id']}",
        data={"template": "Ich möchte Kaffee."},
    )

    assert response.status_code == 400
