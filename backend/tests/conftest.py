from __future__ import annotations

from pathlib import Path

import pytest

from src import database


@pytest.fixture
def initialized_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_FILE", tmp_path / "app.sqlite")
    database.init_db()
    return tmp_path
