from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetItem:
    audio_id: str
    audio_file: str
    source: str
    transcript: str


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", unicodedata.normalize("NFKC", text).casefold()))


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_token in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_token in enumerate(hypothesis, start=1):
            current.append(min(previous[hypothesis_index - 1] + (reference_token != hypothesis_token), current[hypothesis_index - 1] + 1, previous[hypothesis_index] + 1))
        previous = current
    return previous[-1]


def metrics(reference: str, prediction: str) -> tuple[int, int, int, int]:
    reference_words = normalize(reference).split()
    predicted_words = normalize(prediction).split()
    reference_characters = list("".join(reference_words))
    predicted_characters = list("".join(predicted_words))
    return (
        edit_distance(reference_words, predicted_words),
        len(reference_words),
        edit_distance(reference_characters, predicted_characters),
        len(reference_characters),
    )


def load_dataset(root: Path) -> list[DatasetItem]:
    labels_path = root / "training-labels.csv"
    if not labels_path.is_file():
        raise ValueError("Dataset does not contain training-labels.csv.")
    items: list[DatasetItem] = []
    with labels_path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            audio_file = row.get("audio_file", "")
            transcript = row.get("transcript", "").strip()
            audio_path = (root / audio_file).resolve()
            if transcript and audio_path.is_file():
                items.append(DatasetItem(row.get("audio_id") or audio_path.stem, audio_file, row.get("source", ""), transcript))
    if not items:
        raise ValueError("Dataset has no usable labeled clips.")
    return items


def select_split(items: list[DatasetItem], split_path: Path, split_name: str) -> list[DatasetItem]:
    with split_path.open(newline="", encoding="utf-8") as input_file:
        audio_ids = {row["audio_id"] for row in csv.DictReader(input_file) if row["split"] == split_name}
    selected = [item for item in items if item.audio_id in audio_ids]
    if not selected:
        raise ValueError(f"Split has no matching {split_name!r} clips: {split_path}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare local faster-whisper models on labeled audio clips.")
    parser.add_argument("dataset", type=Path, help="Directory with training-labels.csv and data/audio files.")
    parser.add_argument("--model", action="append", required=True, help="Model name. Repeat to compare models.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/asr-benchmark"))
    parser.add_argument("--language", default="de")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--split", type=Path, help="Optional split.csv file. Benchmarks its evaluation clips by default.")
    parser.add_argument("--split-name", default="evaluation")
    arguments = parser.parse_args()

    from faster_whisper import WhisperModel

    root = arguments.dataset.resolve()
    items = load_dataset(root)
    if arguments.split:
        items = select_split(items, arguments.split, arguments.split_name)
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    details: list[dict[str, str | int | float]] = []
    summaries: list[dict[str, str | int | float]] = []
    for model_specification in arguments.model:
        model_name, model_path = model_specification.split("=", 1) if "=" in model_specification else (model_specification, model_specification)
        print(f"Loading {model_name}", file=sys.stderr)
        model = WhisperModel(model_path, device=arguments.device, compute_type=arguments.compute_type)
        total_word_errors = total_words = total_character_errors = total_characters = 0
        total_seconds = 0.0
        for item in items:
            started = time.perf_counter()
            segments, _ = model.transcribe(str(root / item.audio_file), language=arguments.language, beam_size=arguments.beam_size, vad_filter=True)
            prediction = " ".join(segment.text.strip() for segment in segments)
            elapsed = time.perf_counter() - started
            word_errors, word_count, character_errors, character_count = metrics(item.transcript, prediction)
            total_word_errors += word_errors
            total_words += word_count
            total_character_errors += character_errors
            total_characters += character_count
            total_seconds += elapsed
            details.append({"model": model_name, "audio_id": item.audio_id, "audio_file": item.audio_file, "expected_transcript": item.transcript, "predicted_transcript": prediction, "word_error_rate": word_errors / word_count, "character_error_rate": character_errors / character_count, "transcription_seconds": f"{elapsed:.3f}"})
        summaries.append({"model": model_name, "clips": len(items), "word_error_rate": total_word_errors / total_words, "character_error_rate": total_character_errors / total_characters, "total_transcription_seconds": f"{total_seconds:.3f}"})
    for path, rows in ((arguments.output_dir / "details.csv", details), (arguments.output_dir / "summary.csv", summaries)):
        with path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Wrote results to {arguments.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
