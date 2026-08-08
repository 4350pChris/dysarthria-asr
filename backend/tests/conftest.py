from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlmodel import Session

from src import database
from src.corpus import create_audio_clip, update_transcription_label
from src.labeling_models import AudioClipCreate, TranscriptionLabelChanges


def connect_test_db(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def make_audio_clip(session: Session, id: str, file_path: str, original_filename: str = "", content_type: str = "", source: str = "whatsapp_upload") -> dict:
    return create_audio_clip(AudioClipCreate(id=id, file_path=file_path, original_filename=original_filename, content_type=content_type, source=source), session)


def change_label(session: Session, audio_id: str, **changes: object) -> dict:
    return update_transcription_label(audio_id, TranscriptionLabelChanges(**changes), session)


@pytest.fixture
def initialized_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(database, "DB_FILE", tmp_path / "app.sqlite")
    database.init_db()
    return tmp_path


@pytest.fixture
def session(initialized_db: Path) -> Session:
    with Session(database.engine, expire_on_commit=False) as db_session:
        yield db_session
