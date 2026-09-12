from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import numpy as np
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from sqlmodel import Session, col, select
from starlette.concurrency import run_in_threadpool

from ..asr import LIVE_VAD_PARAMETERS, transcribe_german, transcribe_german_segments
from ..corpus import create_audio_clip, update_transcription_label
from ..database import get_session
from ..emoji_normalizer import emoji_from_spoken_name, replace_spoken_emojis
from ..labeling_models import AudioClipCreate, TranscriptionLabelChanges
from ..math_normalizer import normalize_german_math
from ..models import AsrSource, AudioClip, AudioSource, TranscriptionLabel
from ..paths import AUDIO_DIR, ROOT

router = APIRouter(prefix="/api")

LIVE_WINDOW_SECONDS = 5
LIVE_STABLE_SECONDS = 1
LIVE_UPDATE_SECONDS = 1
# ponytail: the last second can change; the final pass is authoritative.


@router.get("/emojis/recent")
def recent_emojis(session: Session = Depends(get_session)) -> list[dict[str, str]]:
    rows = session.exec(
        select(TranscriptionLabel.transcript, TranscriptionLabel.asr_text)
        .join(AudioClip)
        .order_by(col(AudioClip.created_at).desc())
        .limit(1_000)
    ).all()
    emojis: list[dict[str, str]] = []
    seen: set[str] = set()
    for transcript, asr_text in rows:
        match = emoji_from_spoken_name(transcript.strip()) or emoji_from_spoken_name(asr_text.strip())
        if not match or match[0] in seen:
            continue
        seen.add(match[0])
        emojis.append({"value": match[0], "name": match[1]})
        if len(emojis) == 8:
            break
    return emojis


def transcribe_pcm_segments(audio: bytes, sample_rate: int) -> list[tuple[float, float, str]]:
    samples = np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32_768
    if sample_rate != 16_000:
        target_size = round(len(samples) * 16_000 / sample_rate)
        samples = np.interp(
            np.linspace(0, len(samples) - 1, target_size),
            np.arange(len(samples)),
            samples,
        ).astype(np.float32)
    return transcribe_german_segments(
        samples,
        vad_parameters=LIVE_VAD_PARAMETERS,
    )


@router.websocket("/transcribe/stream")
async def stream_transcription(
    websocket: WebSocket,
    sample_rate: int = Query(16_000, ge=8_000, le=48_000),
) -> None:
    await websocket.accept()
    audio = bytearray()
    window_start = 0.0
    committed_until = 0.0
    committed: list[str] = []
    bytes_per_second = sample_rate * 2

    async def receive_audio() -> None:
        nonlocal window_start
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                return
            if message.get("text"):
                return
            chunk = message.get("bytes")
            if not chunk:
                continue
            audio.extend(chunk)
            while len(audio) > LIVE_WINDOW_SECONDS * bytes_per_second:
                del audio[:bytes_per_second]
                window_start += 1

    async def send_updates() -> None:
        nonlocal committed_until
        while True:
            await asyncio.sleep(LIVE_UPDATE_SECONDS)
            if not audio:
                continue
            snapshot = bytes(audio)
            snapshot_start = window_start
            received_until = snapshot_start + len(snapshot) / bytes_per_second
            segments = await run_in_threadpool(transcribe_pcm_segments, snapshot, sample_rate)
            stable_until = received_until - LIVE_STABLE_SECONDS
            partial: list[str] = []
            for start, end, text in segments:
                absolute_end = snapshot_start + end
                if absolute_end <= stable_until and absolute_end > committed_until:
                    committed.append(text)
                    committed_until = absolute_end
                elif absolute_end > committed_until:
                    partial.append(text)
            try:
                await websocket.send_json({
                    "type": "partial",
                    "committed": " ".join(committed),
                    "partial": " ".join(partial),
                })
            except RuntimeError as error:
                if "websocket.close" in str(error):
                    return
                raise

    try:
        async with asyncio.TaskGroup() as tasks:
            receive_task = tasks.create_task(receive_audio())
            send_task = tasks.create_task(send_updates())
            await receive_task
            send_task.cancel()
    except WebSocketDisconnect:
        return
@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "").suffix or ".webm"
    audio_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{audio_id}{suffix}"
    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Upload a non-empty audio file.")
    audio_path.write_bytes(contents)

    try:
        transcript = transcribe_german(audio_path).strip()
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    if not transcript:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Keine Sprache erkannt.")

    relative_audio_path = str(audio_path.relative_to(ROOT))
    create_audio_clip(AudioClipCreate(
        id=audio_id,
        file_path=relative_audio_path,
        original_filename=audio.filename or "recording.webm",
        content_type=audio.content_type or "",
        source=AudioSource.APP_RECORDING,
    ), session=session)
    update_transcription_label(
        audio_id,
        TranscriptionLabelChanges(
        asr_text=transcript,
            asr_source=AsrSource.SERVER,
        ), session,
    )
    emoji_text = replace_spoken_emojis(transcript)
    emoji_match = emoji_from_spoken_name(transcript)
    math = normalize_german_math(transcript)
    return {
        "audio_id": audio_id,
        "audio_path": relative_audio_path,
        "raw_transcript": transcript,
        "emoji_text": emoji_text,
        "emoji_value": emoji_match[0] if emoji_match else "",
        "emoji_name": emoji_match[1] if emoji_match else "",
        "math_corrected_text": math.corrected_text,
        "math_number_text": math.number_text,
        "math_text": math.math_text,
    }
