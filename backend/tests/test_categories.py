from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app


def test_category_endpoint_renames_and_deletes_its_phrases(initialized_db: Path) -> None:
    client = TestClient(create_app())
    category = client.post("/api/categories", data={"name": "Test"}).json()
    client.post("/api/phrases", data={"category_id": category["id"], "text": "Hallo"})

    renamed = client.patch(f"/api/categories/{category['id']}", data={"name": "Neu"})

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Neu"
    assert client.delete(f"/api/categories/{category['id']}").status_code == 200
    assert all(item["id"] != category["id"] for item in client.get("/api/categories").json())
    assert all(item["category"] != "Neu" for item in client.get("/api/phrases").json())
