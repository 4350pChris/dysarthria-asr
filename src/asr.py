from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    return WhisperModel("small", device="cpu", compute_type="int8")


def transcribe_german(audio_path: Path) -> str:
    segments, _ = _model().transcribe(
        str(audio_path),
        language="de",
        beam_size=5,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()

