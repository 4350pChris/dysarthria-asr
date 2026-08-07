from __future__ import annotations

import pytest

from src import asr


def test_model_settings_require_model(monkeypatch) -> None:
    monkeypatch.delenv("ASR_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="Set ASR_MODEL"):
        asr.model_settings()


def test_model_settings_split_revision_from_model_reference(monkeypatch) -> None:
    monkeypatch.setenv("ASR_MODEL", "dysarthria-asr/amsel@v1")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    assert asr.model_settings() == {
        "model_size_or_path": "dysarthria-asr/amsel",
        "device": "cpu",
        "compute_type": "int8",
        "revision": "v1",
        "use_auth_token": "test-token",
    }
