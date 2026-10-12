from __future__ import annotations

import argparse
import csv
import hashlib
import io
import math
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

from align_reading import normalise


LABEL_FIELDS = ["audio_id", "audio_file", "source", "transcript"]
SPLIT_FIELDS = ["audio_id", "split", "audio_file", "transcript"]
APP_ZIP_URL = "https://asr.ennen.dev/api/labeling/training-data.zip"
READING_DATASET = Path("data/datasets/reading-v2")
OUTPUT_DIR = Path("data/datasets/current")
MAX_CLIP_SECONDS = 25
MAX_ALIGNMENT_SECONDS = 300


def normalized_transcript(text: str) -> str:
    return " ".join("".join(character if character.isalnum() else " " for character in unicodedata.normalize("NFKC", text).casefold()).split())


def split_name(transcript: str) -> str:
    bucket = int.from_bytes(hashlib.sha256(f"dysarthria-asr-split-v1:{normalized_transcript(transcript)}".encode()).digest()[:8], "big") % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def app_items(archive_path: Path, temporary_dir: Path) -> list[tuple[str, Path, str, str]]:
    with zipfile.ZipFile(archive_path) as archive:
        rows = list(csv.DictReader(io.StringIO(archive.read("training-labels.csv").decode("utf-8"))))
        items = []
        for row in rows:
            transcript = row.get("transcript", "").strip()
            audio_file = row.get("audio_file", "")
            if not transcript or not audio_file.startswith("data/audio/"):
                continue
            target = temporary_dir / Path(audio_file).name
            with archive.open(audio_file) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            items.append((f"app-{row['audio_id']}", target, "app_recording", transcript))
    return items


def download_app_zip(destination: Path) -> None:
    with urllib.request.urlopen(APP_ZIP_URL, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def reading_items(dataset_dir: Path) -> list[tuple[str, Path, str, str]]:
    with (dataset_dir / "training-labels.csv").open(newline="", encoding="utf-8") as input_file:
        return [
            (f"reading-{row['audio_id']}", dataset_dir / row["audio_file"], "reading", row["transcript"].strip())
            for row in csv.DictReader(input_file)
            if row.get("transcript", "").strip()
        ]


def convert_to_wav(source: Path, output: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(output)],
        check=True,
    )


def aligned_clips(text: str, timed: list, duration: float) -> list[tuple[float, float, str]]:
    tokens = [match for match in re.finditer(r"\S+", text) if any(char.isalnum() for char in match.group())]
    if not tokens or len(tokens) != len(timed):
        raise ValueError("Alignment does not cover every transcript word.")
    previous_end = 0.0
    for token, word in zip(tokens, timed):
        if normalise(token.group()) != normalise(word.text):
            raise ValueError("Alignment words differ from the saved transcript.")
        if not (math.isfinite(word.start_time) and math.isfinite(word.end_time)
                and previous_end <= word.start_time < word.end_time <= duration):
            raise ValueError("Alignment has invalid or overlapping word times.")
        if word.end_time - word.start_time > MAX_CLIP_SECONDS - .3:
            raise ValueError("One aligned word exceeds the clip length limit.")
        previous_end = word.end_time

    clips = []
    first = 0
    while first < len(timed):
        start = max(0, timed[first].start_time - .15, timed[first - 1].end_time if first else 0)
        last = first
        while last + 1 < len(timed) and timed[last + 1].end_time + .15 - start <= MAX_CLIP_SECONDS:
            last += 1
        end = min(duration, timed[last].end_time + .15, timed[last + 1].start_time if last + 1 < len(timed) else duration)
        text_start = tokens[first].start() if first else 0
        text_end = tokens[last + 1].start() if last + 1 < len(tokens) else len(text)
        clips.append((start, end, text[text_start:text_end].strip()))
        first = last + 1
    return clips


def load_aligner():
    import torch
    from qwen_asr import Qwen3ForcedAligner

    # CPU also works on download hosts without a CUDA GPU.
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    return Qwen3ForcedAligner.from_pretrained(
        "Qwen/Qwen3-ForcedAligner-0.6B",
        dtype=torch.bfloat16 if device == "cuda:0" else torch.float32,
        device_map=device,
    )


def prepare_items(items: list, output_dir: Path) -> tuple[list[dict], list[dict], list[dict]]:
    import soundfile as sf
    from make_training_clips import cut_clip

    audio_dir = output_dir / "data" / "audio"
    audio_dir.mkdir(parents=True)
    labels, split_rows, excluded = [], [], []
    aligner = None
    for audio_id, source_audio, source, transcript in items:
        if not source_audio.is_file():
            raise FileNotFoundError(source_audio)
        target = audio_dir / f"{audio_id}.wav"
        convert_to_wav(source_audio, target)
        info = sf.info(target)
        duration = info.frames / info.samplerate
        if duration <= 0:
            raise ValueError(f"Empty audio: {audio_id}")
        clips = [(audio_id, target, transcript)]
        if duration > MAX_CLIP_SECONDS:
            if duration <= MAX_ALIGNMENT_SECONDS and aligner is None:
                aligner = load_aligner()
            try:
                if duration > MAX_ALIGNMENT_SECONDS:
                    raise ValueError("Recording exceeds the five-minute alignment limit.")
                timed = aligner.align(audio=str(target), text=transcript, language="German")[0]
                parts = aligned_clips(transcript, list(timed), duration)
            except ValueError as error:
                excluded.append({"audio_id": audio_id, "reason": str(error)})
                print(f"Excluded {audio_id}: {error}")
                target.unlink()
                continue
            clips = []
            for index, (start, end, text) in enumerate(parts, 1):
                clip_id = f"{audio_id}-clip-{index:03d}"
                clip_path = audio_dir / f"{clip_id}.wav"
                cut_clip(target, start, end, clip_path)
                clips.append((clip_id, clip_path, text))
            target.unlink()
        # Use the full source text so sibling clips cannot enter different splits.
        split = split_name(transcript)
        for clip_id, clip_path, text in clips:
            row = {"audio_id": clip_id, "audio_file": clip_path.relative_to(output_dir).as_posix(), "source": source, "transcript": text}
            labels.append(row)
            split_rows.append({"audio_id": clip_id, "split": split, "audio_file": row["audio_file"], "transcript": text})
    return labels, split_rows, excluded


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the current training dataset and its stable three-way split.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing output dataset.")
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="dysarthria-asr-app-data-") as temporary_name:
        temporary_dir = Path(temporary_name)
        app_zip = temporary_dir / "training-data.zip"
        download_app_zip(app_zip)
        if OUTPUT_DIR.exists() and not arguments.replace:
            raise FileExistsError(f"Output directory already exists: {OUTPUT_DIR}. Use --replace to rebuild it.")
        staging_dir = temporary_dir / "dataset"
        items = app_items(app_zip, temporary_dir) + reading_items(READING_DATASET)
        labels, split_rows, excluded = prepare_items(items, staging_dir)
        split_counts = {name: sum(row["split"] == name for row in split_rows) for name in ("train", "validation", "test")}
        if not all(split_counts.values()):
            raise ValueError(f"Dataset needs clips in every split: {split_counts}")
        for filename, fields, rows in (
            ("training-labels.csv", LABEL_FIELDS, labels),
            ("split.csv", SPLIT_FIELDS, split_rows),
            ("excluded-recordings.csv", ["audio_id", "reason"], excluded),
        ):
            with (staging_dir / filename).open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging_dir), OUTPUT_DIR)
    print(f"Wrote split: {split_counts}")
    print(f"Wrote {len(labels)} clips to {OUTPUT_DIR}")
    print(f"Excluded {len(excluded)} recordings; see {OUTPUT_DIR / 'excluded-recordings.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
