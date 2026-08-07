from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path


def model_settings() -> dict[str, str | None]:
    return {
        "model_size_or_path": os.environ.get("ASR_MODEL", "large-v3-turbo"),
        "device": os.environ.get("ASR_DEVICE", "cpu"),
        "compute_type": os.environ.get("ASR_COMPUTE_TYPE", "int8"),
        "download_root": os.environ.get("ASR_MODEL_CACHE_DIR"),
        "revision": os.environ.get("ASR_MODEL_REVISION"),
        "use_auth_token": os.environ.get("ASR_HF_TOKEN"),
    }


@lru_cache(maxsize=1)
def _model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Run `pip install -r requirements.txt`."
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
