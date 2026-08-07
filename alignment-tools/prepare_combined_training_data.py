from __future__ import annotations

import argparse
import csv
import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


LABEL_FIELDS = ["audio_id", "audio_file", "source", "transcript"]


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
    parser = argparse.ArgumentParser(description="Combine app training ZIP data with prepared reading clips.")
    parser.add_argument("app_zip", type=Path)
    parser.add_argument("reading_dataset", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("training-combined"))
    arguments = parser.parse_args()
    if arguments.output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {arguments.output_dir}")
    audio_dir = arguments.output_dir / "data" / "audio"
    audio_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="dysarthria-asr-app-data-") as temporary_name:
        items = app_items(arguments.app_zip, Path(temporary_name)) + reading_items(arguments.reading_dataset)
        labels = []
        for audio_id, source_audio, source, transcript in items:
            if not source_audio.is_file():
                raise FileNotFoundError(source_audio)
            target = audio_dir / f"{audio_id}.wav"
            convert_to_wav(source_audio, target)
            labels.append({"audio_id": audio_id, "audio_file": target.relative_to(arguments.output_dir).as_posix(), "source": source, "transcript": transcript})
    with (arguments.output_dir / "training-labels.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(labels)
    print(f"Wrote {len(labels)} clips to {arguments.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
