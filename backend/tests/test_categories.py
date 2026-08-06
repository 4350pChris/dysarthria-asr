from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app


def test_category_endpoint_renames_and_deletes_its_phrases(initialized_db: Path) -> None:
    client = TestClient(create_app())
    created_category = client.post("/api/categories", data={"name": "Test"})
    assert created_category.status_code == 201
    category = created_category.json()
    duplicate_category = client.post("/api/categories", data={"name": "Test"})
    assert duplicate_category.status_code == 409
    assert duplicate_category.json()["detail"][0]["type"] == "category_exists"
    assert duplicate_category.json()["detail"][0]["loc"] == ["body", "name"]
    created_phrase = client.post("/api/phrases", data={"category_id": category["id"], "text": "Hallo"})
    assert created_phrase.status_code == 201

    renamed = client.patch(f"/api/categories/{category['id']}", data={"name": "Neu"})

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Neu"
    deleted = client.delete(f"/api/categories/{category['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert all(item["id"] != category["id"] for item in client.get("/api/categories").json())
    assert all(item["category"] != "Neu" for item in client.get("/api/phrases").json())


def test_phrase_routes_return_conflicts_and_no_content(initialized_db: Path) -> None:
    client = TestClient(create_app())
    category = client.post("/api/categories", data={"name": "Test"}).json()
    first = client.post("/api/phrases", data={"category_id": category["id"], "text": "Hallo"})
    second = client.post("/api/phrases", data={"category_id": category["id"], "text": "Tschüss"})

    assert first.status_code == 201
    assert second.status_code == 201
    duplicate = client.post(
        "/api/phrases",
        data={"category_id": category["id"], "text": "Hallo"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"][0]["type"] == "phrase_exists"
    assert duplicate.json()["detail"][0]["loc"] == ["body", "text"]

    renamed = client.patch(
        f"/api/phrases/{second.json()['id']}",
        data={"text": "Hallo"},
    )
    assert renamed.status_code == 409
    assert renamed.json()["detail"][0]["type"] == "phrase_exists"

    deleted = client.delete(f"/api/phrases/{first.json()['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
