from __future__ import annotations

import pytest

from src import asr
from src.routers import transcription


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


def test_model_settings_accept_an_explicit_reference(monkeypatch) -> None:
    monkeypatch.setenv("ASR_MODEL", "dysarthria-asr/amsel@v6")
    monkeypatch.delenv("HF_TOKEN", raising=False)

    settings = asr.model_settings("local/ct2-small")
    assert settings["model_size_or_path"] == "local/ct2-small"
    assert settings["revision"] is None


def test_live_transcription_uses_fast_settings(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(transcription, "transcribe_german_segments", lambda audio, **kwargs: captured.update(kwargs) or [])

    transcription.transcribe_pcm_segments(b"\x00\x00" * 16_000, 16_000)
    assert captured["beam_size"] == 1
    assert captured["condition_on_previous_text"] is False
    assert captured["model_reference"] is None

    monkeypatch.setenv("ASR_LIVE_MODEL", "dysarthria-asr/amsel-small-ct2")
    # Beam size is fixed at 1 for live previews; the knob must not reappear.
    monkeypatch.setenv("ASR_LIVE_BEAM_SIZE", "5")
    transcription.transcribe_pcm_segments(b"\x00\x00" * 16_000, 16_000)
    assert captured["beam_size"] == 1
    assert captured["model_reference"] == "dysarthria-asr/amsel-small-ct2"
