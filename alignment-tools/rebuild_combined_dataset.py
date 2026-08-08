from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


LABEL_FIELDS = ["audio_id", "audio_file", "source", "transcript"]


def read_rows(dataset: Path, source: str | None = None) -> list[dict[str, str]]:
    with (dataset / "training-labels.csv").open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    return [row for row in rows if row.get("transcript", "").strip() and (source is None or row.get("source") == source)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine existing app labels with reviewed reading clips.")
    parser.add_argument("app_dataset", type=Path, help="Existing combined dataset with app_recording rows.")
    parser.add_argument("reading_dataset", type=Path, help="Reviewed reading dataset.")
    parser.add_argument("--output-dir", type=Path, default=Path("training-combined-v2"))
    arguments = parser.parse_args()

    if arguments.output_dir.exists():
        raise FileExistsError(f"{arguments.output_dir} already exists.")
    app_rows = read_rows(arguments.app_dataset, source="app_recording")
    reading_rows = read_rows(arguments.reading_dataset)
    output_audio = arguments.output_dir / "data" / "audio"
    output_audio.mkdir(parents=True)
    labels: list[dict[str, str]] = []
    for dataset, rows in ((arguments.app_dataset, app_rows), (arguments.reading_dataset, reading_rows)):
        for row in rows:
            source_audio = dataset / row["audio_file"]
            if not source_audio.is_file():
                raise FileNotFoundError(source_audio)
            audio_id = row["audio_id"]
            target = output_audio / f"{audio_id}.wav"
            if target.exists():
                raise ValueError(f"Duplicate audio ID: {audio_id}")
            shutil.copy2(source_audio, target)
            labels.append(
                {
                    "audio_id": audio_id,
                    "audio_file": target.relative_to(arguments.output_dir).as_posix(),
                    "source": row["source"],
                    "transcript": row["transcript"].strip(),
                }
            )
    with (arguments.output_dir / "training-labels.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(labels)
    print(f"Wrote {len(app_rows)} app clips and {len(reading_rows)} reading clips to {arguments.output_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
