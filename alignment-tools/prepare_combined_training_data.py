from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.request
import zipfile
from pathlib import Path


LABEL_FIELDS = ["audio_id", "audio_file", "source", "transcript"]
SPLIT_FIELDS = ["audio_id", "split", "audio_file", "transcript"]
APP_ZIP_URL = "https://asr.ennen.dev/api/labeling/training-data.zip"
READING_DATASET = Path("data/datasets/reading-v2")
OUTPUT_DIR = Path("data/datasets/current")


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the current training dataset and its stable three-way split.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing output dataset.")
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="dysarthria-asr-app-data-") as temporary_name:
        temporary_dir = Path(temporary_name)
        app_zip = temporary_dir / "training-data.zip"
        download_app_zip(app_zip)
        if OUTPUT_DIR.exists():
            if not arguments.replace:
                raise FileExistsError(f"Output directory already exists: {OUTPUT_DIR}. Use --replace to rebuild it.")
            shutil.rmtree(OUTPUT_DIR)
        audio_dir = OUTPUT_DIR / "data" / "audio"
        audio_dir.mkdir(parents=True)
        items = app_items(app_zip, temporary_dir) + reading_items(READING_DATASET)
        labels = []
        for audio_id, source_audio, source, transcript in items:
            if not source_audio.is_file():
                raise FileNotFoundError(source_audio)
            target = audio_dir / f"{audio_id}.wav"
            convert_to_wav(source_audio, target)
            labels.append({"audio_id": audio_id, "audio_file": target.relative_to(OUTPUT_DIR).as_posix(), "source": source, "transcript": transcript})
    with (OUTPUT_DIR / "training-labels.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(labels)
    split_rows = [{"audio_id": row["audio_id"], "split": split_name(row["transcript"]), "audio_file": row["audio_file"], "transcript": row["transcript"]} for row in labels]
    split_counts = {name: sum(row["split"] == name for row in split_rows) for name in ("train", "validation", "test")}
    if not all(split_counts.values()):
        raise ValueError(f"Dataset needs clips in every split: {split_counts}")
    with (OUTPUT_DIR / "split.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=SPLIT_FIELDS)
        writer.writeheader()
        writer.writerows(split_rows)
    print(f"Wrote split: {split_counts}")
    print(f"Wrote {len(labels)} clips to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
