from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import TypedDict

import numpy as np

TOLERANT_VAD_PARAMETERS = {
    "threshold": 0.35,
    "min_silence_duration_ms": 3_000,
    "speech_pad_ms": 600,
}

LIVE_VAD_PARAMETERS = {
    "threshold": 0.35,
    "min_silence_duration_ms": 500,
    "speech_pad_ms": 200,
}

INFERENCE_LOCK = Lock()


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
    return " ".join(text for _, _, text in transcribe_german_segments(audio_path)).strip()


def warm_model() -> None:
    _model()


def transcribe_german_segments(
    audio: Path | np.ndarray,
    *,
    vad_parameters: dict = TOLERANT_VAD_PARAMETERS,
    chunk_length: int | None = None,
) -> list[tuple[float, float, str]]:
    with INFERENCE_LOCK:
        segments, _ = _model().transcribe(
            str(audio) if isinstance(audio, Path) else audio,
            language="de",
            beam_size=1,
            vad_filter=True,
            vad_parameters=vad_parameters,
            chunk_length=chunk_length,
        )
        return [
            (segment.start, segment.end, segment.text.strip())
            for segment in segments
            if segment.text.strip()
        ]
