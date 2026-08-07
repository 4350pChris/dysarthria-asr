from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


LABEL_FIELDS = ["audio_id", "audio_file", "source", "transcript"]


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    if not rows:
        raise ValueError(f"{csv_path} has no clip rows.")
    required = {"clip_id", "text", "start_seconds", "end_seconds"}
    if not required.issubset(rows[0]):
        raise ValueError(f"{csv_path} is not an alignment CSV.")
    return rows


def cut_clip(audio: Path, start: float, end: float, output: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(audio),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Cut reviewed reading alignment rows into Whisper training clips.")
    parser.add_argument(
        "--part",
        action="append",
        nargs=2,
        metavar=("ALIGNMENT_CSV", "AUDIO_FILE"),
        required=True,
        help="One reviewed alignment CSV and its matching audio part. Repeat for every part.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("training-reading"))
    arguments = parser.parse_args()

    output_dir = arguments.output_dir
    audio_dir = output_dir / "data" / "audio"
    labels_path = output_dir / "training-labels.csv"
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    audio_dir.mkdir(parents=True)

    labels: list[dict[str, str]] = []
    for csv_name, audio_name in arguments.part:
        csv_path = Path(csv_name)
        audio_path = Path(audio_name)
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        source = csv_path.stem.removesuffix("-alignment")
        for row in read_rows(csv_path):
            transcript = row["text"].strip()
            start = float(row["start_seconds"])
            end = float(row["end_seconds"])
            if not transcript or end <= start:
                raise ValueError(f"Invalid row {row['clip_id']} in {csv_path}")
            audio_id = f"reading-{source}-{int(row['clip_id']):03d}"
            clip_path = audio_dir / f"{audio_id}.wav"
            cut_clip(audio_path, start, end, clip_path)
            labels.append(
                {
                    "audio_id": audio_id,
                    "audio_file": clip_path.relative_to(output_dir).as_posix(),
                    "source": "reading",
                    "transcript": transcript,
                }
            )

    with labels_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(labels)
    print(f"Wrote {len(labels)} WAV clips and {labels_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
