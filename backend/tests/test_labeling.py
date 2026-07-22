from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src import database
from src.routers import labeling


def test_import_creates_whatsapp_draft_labels(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: "hallo welt")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/labeling/import",
        files=[
            ("files", ("one.ogg", b"audio one", "audio/ogg")),
            ("files", ("two.ogg", b"audio two", "audio/ogg")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 2
    assert body["counts"]["draft"] == 2

    with database.connect_db() as db:
        clips = db.execute("SELECT source, original_filename FROM audio_clips").fetchall()
        labels = db.execute("SELECT asr_text, status FROM transcription_labels").fetchall()
    assert [dict(row)["source"] for row in clips] == ["whatsapp_upload", "whatsapp_upload"]
    assert {dict(row)["original_filename"] for row in clips} == {"one.ogg", "two.ogg"}
    assert [dict(row) for row in labels] == [
        {"asr_text": "hallo welt", "status": "draft"},
        {"asr_text": "hallo welt", "status": "draft"},
    ]


def test_import_accepts_ogg_with_octet_stream_content_type(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: "hallo")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/labeling/import",
        files=[("files", ("whatsapp.ogg", b"audio bytes", "application/octet-stream"))],
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 1


def test_labeling_update_and_default_export_include_only_training_rows(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: "kaffee bitte")

    from src.app import create_app

    client = TestClient(create_app())
    imported = client.post(
        "/api/labeling/import",
        files=[
            ("files", ("labeled.ogg", b"audio one", "audio/ogg")),
            ("files", ("unsure.ogg", b"audio two", "audio/ogg")),
        ],
    ).json()["items"]

    first_id = imported[0]["audio_id"]
    second_id = imported[1]["audio_id"]
    response = client.patch(
        f"/api/labeling/items/{first_id}",
        data={"transcript": "Kaffee bitte.", "status": "labeled", "unsure": "false", "notes": ""},
    )
    assert response.status_code == 200
    assert response.json()["item"]["status"] == "labeled"
    client.patch(
        f"/api/labeling/items/{second_id}",
        data={"transcript": "Unsicher.", "status": "labeled", "unsure": "true", "notes": ""},
    )

    export = client.get("/api/labeling/export.csv")
    text = export.text
    assert "Kaffee bitte." in text
    assert "Unsicher." not in text


def test_next_item_returns_oldest_draft(initialized_db: Path, monkeypatch) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: Path(audio_path).stem)

    from src.app import create_app

    client = TestClient(create_app())
    imported = client.post(
        "/api/labeling/import",
        files=[
            ("files", ("first.ogg", b"audio one", "audio/ogg")),
            ("files", ("second.ogg", b"audio two", "audio/ogg")),
        ],
    ).json()["items"]
    client.patch(
        f"/api/labeling/items/{imported[0]['audio_id']}",
        data={"transcript": "skip", "status": "skipped", "unsure": "false", "notes": ""},
    )

    response = client.get("/api/labeling/items/next")

    assert response.status_code == 200
    assert response.json()["item"]["audio_id"] == imported[1]["audio_id"]
