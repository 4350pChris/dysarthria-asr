from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import TypedDict


class ModelSettings(TypedDict):
    model_size_or_path: str
    device: str
    compute_type: str
    revision: str | None
    use_auth_token: str | None


def model_settings() -> ModelSettings:
    model_reference = os.environ.get("ASR_MODEL", "").strip()
    if not model_reference:
        raise RuntimeError("Set ASR_MODEL to a full model ID, optionally followed by @revision.")
    model_name, separator, revision = model_reference.rpartition("@")
    if separator and (not model_name or not revision):
        raise RuntimeError("ASR_MODEL must use model-id@revision when it includes @.")
    if not separator:
        model_name = model_reference
        revision = None
    return {
        "model_size_or_path": model_name,
        "device": "cpu",
        "compute_type": "int8",
        "revision": revision,
        "use_auth_token": os.environ.get("HF_TOKEN"),
    }


@lru_cache(maxsize=1)
def _model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Run `uv sync`."
        ) from exc

    return WhisperModel(**model_settings())


def transcribe_german(audio_path: Path) -> str:
    segments, _ = _model().transcribe(
        str(audio_path),
        language="de",
        beam_size=5,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
