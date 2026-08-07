from __future__ import annotations

from src import asr


def test_model_settings_use_defaults(monkeypatch) -> None:
    for name in ("ASR_MODEL", "ASR_DEVICE", "ASR_COMPUTE_TYPE", "ASR_MODEL_CACHE_DIR", "ASR_MODEL_REVISION", "ASR_HF_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    assert asr.model_settings() == {
        "model_size_or_path": "large-v3-turbo",
        "device": "cpu",
        "compute_type": "int8",
        "download_root": None,
        "revision": None,
        "use_auth_token": None,
    }


def test_model_settings_allow_deployed_model(monkeypatch) -> None:
    monkeypatch.setenv("ASR_MODEL", "your-org/speaker-v1")
    monkeypatch.setenv("ASR_DEVICE", "cpu")
    monkeypatch.setenv("ASR_COMPUTE_TYPE", "int8")
    monkeypatch.setenv("ASR_MODEL_CACHE_DIR", "/models/cache")
    monkeypatch.setenv("ASR_MODEL_REVISION", "0123456789abcdef")
    monkeypatch.setenv("ASR_HF_TOKEN", "test-token")

    assert asr.model_settings() == {
        "model_size_or_path": "your-org/speaker-v1",
        "device": "cpu",
        "compute_type": "int8",
        "download_root": "/models/cache",
        "revision": "0123456789abcdef",
        "use_auth_token": "test-token",
    }
