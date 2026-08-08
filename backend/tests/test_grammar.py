from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app
from src.candidates import read_generated_candidates


def test_grammar_endpoint_updates_generated_candidates(initialized_db: Path, session) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    value = next(item for item in thing_slot["values"] if item["value"] == "Kaffee")

    response = client.patch(
        f"/api/grammar/values/{value['id']}",
        json={"value": "Kakao"},
    )

    assert response.status_code == 200
    generated_texts = {item["text"] for item in read_generated_candidates(session)}
    assert "Ich möchte Kakao." in generated_texts
    assert "Ich möchte Kaffee." not in generated_texts


def test_grammar_endpoint_updates_pattern_templates(initialized_db: Path, session) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    pattern = next(item for item in thing_slot["patterns"] if item["template"] == "Ich möchte {thing_acc}.")

    response = client.patch(
        f"/api/grammar/patterns/{pattern['id']}",
        json={"template": "Bitte bring mir {thing_acc}."},
    )

    assert response.status_code == 200
    generated_texts = {item["text"] for item in read_generated_candidates(session)}
    assert "Bitte bring mir Kaffee." in generated_texts
    assert "Ich möchte Kaffee." not in generated_texts


def test_grammar_pattern_requires_its_placeholder(initialized_db: Path) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    pattern = next(item for item in thing_slot["patterns"] if item["template"] == "Ich möchte {thing_acc}.")

    response = client.patch(
        f"/api/grammar/patterns/{pattern['id']}",
        json={"template": "Ich möchte Kaffee."},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "grammar_placeholder_invalid"


def test_grammar_routes_return_conflict_for_duplicate_slot_entries(initialized_db: Path) -> None:
    client = TestClient(create_app())
    grammar = client.get("/api/grammar").json()
    thing_slot = next(slot for slot in grammar if slot["name"] == "thing_acc")
    first_pattern, second_pattern = thing_slot["patterns"][:2]
    first_value, second_value = thing_slot["values"][:2]

    duplicate_pattern = client.patch(
        f"/api/grammar/patterns/{second_pattern['id']}",
        json={"template": first_pattern["template"]},
    )
    assert duplicate_pattern.status_code == 409
    assert duplicate_pattern.json()["detail"][0]["type"] == "grammar_pattern_exists"

    duplicate_value = client.patch(
        f"/api/grammar/values/{second_value['id']}",
        json={"value": first_value["value"]},
    )
    assert duplicate_value.status_code == 409
    assert duplicate_value.json()["detail"][0]["type"] == "grammar_value_exists"
