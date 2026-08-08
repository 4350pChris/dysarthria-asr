from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from src import database
from src.corpus import create_audio_clip, upsert_transcription_label
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


def test_import_whatsapp_zip_filters_audio_by_sender(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: Path(audio_path).name)
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr(
            "_chat.txt",
            "\n".join(
                [
                    "22.07.2026, 10:00 - Target Person: 00000001-AUDIO-2026-07-22-10-00-00.opus",
                    "22.07.2026, 10:01 - Friend: 00000002-AUDIO-2026-07-22-10-01-00.opus",
                ]
            ),
        )
        archive.writestr("00000001-AUDIO-2026-07-22-10-00-00.opus", b"target audio")
        archive.writestr("00000002-AUDIO-2026-07-22-10-01-00.opus", b"friend audio")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/labeling/import",
        data={"target_sender": "Target Person"},
        files=[("files", ("whatsapp.zip", export.getvalue(), "application/zip"))],
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 1
    with database.connect_db() as db:
        row = db.execute("SELECT original_filename FROM audio_clips").fetchone()
    assert row["original_filename"] == "00000001-AUDIO-2026-07-22-10-00-00.opus"


def test_import_senders_lists_people_with_audio_messages(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr(
            "_chat.txt",
            "\n".join(
                [
                    "22.07.2026, 10:00 - Target Person: one.opus",
                    "22.07.2026, 10:01 - Friend: two.ogg",
                    "22.07.2026, 10:02 - Text Only: Hello",
                ]
            ),
        )
        archive.writestr("one.opus", b"target audio")
        archive.writestr("two.ogg", b"friend audio")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/labeling/import/senders",
        files=[("archive", ("whatsapp.zip", export.getvalue(), "application/zip"))],
    )

    assert response.status_code == 200
    assert response.json() == {"senders": ["Friend", "Target Person"]}


def test_import_whatsapp_zip_without_sender_imports_all_audio(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: "recognized")
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr("_chat.txt", "")
        archive.writestr("one.opus", b"one")
        archive.writestr("two.ogg", b"two")

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/labeling/import",
        files=[("files", ("whatsapp.zip", export.getvalue(), "application/zip"))],
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 2


def test_import_does_not_store_audio_without_asr_text(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    transcripts = iter(["  ", "hallo"])
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: next(transcripts))

    from src.app import create_app

    response = TestClient(create_app()).post(
        "/api/labeling/import",
        files=[
            ("files", ("empty.ogg", b"empty audio", "audio/ogg")),
            ("files", ("speech.ogg", b"speech audio", "audio/ogg")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert response.json()["skipped"] == 1
    with database.connect_db() as db:
        clips = db.execute("SELECT original_filename, file_path FROM audio_clips").fetchall()
    assert [row["original_filename"] for row in clips] == ["speech.ogg"]
    assert (initialized_db / clips[0]["file_path"]).exists()
    assert len(list((initialized_db / "audio").glob("*.ogg"))) == 1


def test_labeling_update_saves_training_ready_and_unsure_rows(
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
        json={"transcript": "Kaffee bitte.", "status": "labeled", "unsure": False, "notes": ""},
    )
    assert response.status_code == 200
    assert response.json()["item"]["status"] == "labeled"
    client.patch(
        f"/api/labeling/items/{second_id}",
        json={"transcript": "Unsicher.", "status": "labeled", "unsure": True, "notes": ""},
    )

def test_training_data_export_includes_labels_and_matching_audio(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    audio_dir = initialized_db / "audio"
    audio_dir.mkdir()
    (audio_dir / "included.ogg").write_bytes(b"included audio")
    (audio_dir / "excluded.ogg").write_bytes(b"excluded audio")
    (audio_dir / "held-out.ogg").write_bytes(b"held out audio")
    create_audio_clip("included", "audio/included.ogg", "included.ogg")
    upsert_transcription_label(
        "included",
        transcript="Kaffee bitte.",
        status="labeled",
        unsure=False,
    )
    create_audio_clip("excluded", "audio/excluded.ogg", "excluded.ogg")
    upsert_transcription_label(
        "excluded",
        transcript="Unsicher.",
        status="labeled",
        unsure=True,
    )
    create_audio_clip("held-out", "audio/held-out.ogg", "held-out.ogg", source="training_reading")
    upsert_transcription_label(
        "held-out",
        transcript="Dieser Satz bleibt für den Test zurück.",
        status="labeled",
        training_split="test",
    )

    from src.app import create_app

    response = TestClient(create_app()).get("/api/labeling/training-data.zip")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "dysarthria-asr-training-data.zip" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "README.txt",
            "training-labels.csv",
            "audio/included.ogg",
        }
        assert archive.read("audio/included.ogg") == b"included audio"
        labels = archive.read("training-labels.csv").decode()
    assert "Kaffee bitte." in labels
    assert "Unsicher." not in labels
    assert "Dieser Satz bleibt für den Test zurück." not in labels


def test_delete_labeling_item_removes_audio_and_label(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    monkeypatch.setattr(labeling, "transcribe_german", lambda audio_path: "recognized")

    from src.app import create_app

    client = TestClient(create_app())
    item = client.post(
        "/api/labeling/import",
        files=[("files", ("empty.ogg", b"audio", "audio/ogg"))],
    ).json()["items"][0]

    response = client.delete(f"/api/labeling/items/{item['audio_id']}")

    assert response.status_code == 200
    assert response.json()["counts"]["total"] == 0
    assert not (initialized_db / item["audio_file"]).exists()
    with database.connect_db() as db:
        assert db.execute("SELECT COUNT(*) FROM audio_clips").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM transcription_labels").fetchone()[0] == 0


def test_labeling_items_can_filter_missing_asr_text(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    monkeypatch.setattr(labeling, "AUDIO_DIR", initialized_db / "audio")
    from src.app import create_app

    client = TestClient(create_app())
    for audio_id, filename, asr_text in [
        ("empty", "empty.ogg", ""),
        ("text", "text.ogg", "has text"),
        ("spaces", "spaces.ogg", "  "),
    ]:
        create_audio_clip(
            id=audio_id,
            file_path=f"audio/{filename}",
            original_filename=filename,
        )
        upsert_transcription_label(audio_id=audio_id, asr_text=asr_text)

    response = client.get("/api/labeling/items?missing_asr=true")

    assert response.status_code == 200
    assert [item["original_filename"] for item in response.json()["items"]] == [
        "empty.ogg",
        "spaces.ogg",
    ]


def test_delete_empty_asr_items_uses_active_filters(
    initialized_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(labeling, "ROOT", initialized_db)
    for audio_id, status, asr_text in [
        ("empty-draft", "draft", ""),
        ("empty-skipped", "skipped", ""),
        ("text-draft", "draft", "text"),
    ]:
        create_audio_clip(id=audio_id, file_path=f"audio/{audio_id}.ogg")
        upsert_transcription_label(audio_id=audio_id, asr_text=asr_text, status=status)

    from src.app import create_app

    client = TestClient(create_app())
    listed = client.get("/api/labeling/items?status=draft&missing_asr=true")
    assert listed.json()["filtered_count"] == 1

    response = client.delete("/api/labeling/items/empty-asr?status=draft")

    assert response.status_code == 200
    assert response.json()["deleted"] == 1
    with database.connect_db() as db:
        remaining = db.execute("SELECT id FROM audio_clips ORDER BY id").fetchall()
    assert [row["id"] for row in remaining] == ["empty-skipped", "text-draft"]
