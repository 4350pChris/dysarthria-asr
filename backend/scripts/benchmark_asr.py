from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path


DETAIL_FIELDS = [
    "model",
    "audio_id",
    "audio_file",
    "source",
    "expected_transcript",
    "predicted_transcript",
    "word_errors",
    "reference_words",
    "word_error_rate",
    "character_errors",
    "reference_characters",
    "character_error_rate",
    "transcription_seconds",
    "error",
]
SUMMARY_FIELDS = [
    "model",
    "successful_clips",
    "failed_clips",
    "reference_words",
    "word_errors",
    "word_error_rate",
    "reference_characters",
    "character_errors",
    "character_error_rate",
    "total_transcription_seconds",
]


@dataclass(frozen=True)
class DatasetItem:
    audio_id: str
    audio_file: str
    source: str
    transcript: str


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", unicodedata.normalize("NFKC", text).casefold()))


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_token in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_token in enumerate(hypothesis, start=1):
            substitution = previous[hypothesis_index - 1] + (reference_token != hypothesis_token)
            insertion = current[hypothesis_index - 1] + 1
            deletion = previous[hypothesis_index] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def word_metrics(reference: str, hypothesis: str) -> tuple[int, int]:
    reference_words = normalize_text(reference).split()
    hypothesis_words = normalize_text(hypothesis).split()
    return edit_distance(reference_words, hypothesis_words), len(reference_words)


def character_metrics(reference: str, hypothesis: str) -> tuple[int, int]:
    reference_characters = list(normalize_text(reference).replace(" ", ""))
    hypothesis_characters = list(normalize_text(hypothesis).replace(" ", ""))
    return edit_distance(reference_characters, hypothesis_characters), len(reference_characters)


def extract_archive(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            try:
                target.relative_to(destination.resolve())
            except ValueError as error:
                raise ValueError(f"Archive contains an unsafe path: {member.filename}") from error
        archive.extractall(destination)


def resolve_dataset_root(dataset_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if dataset_path.is_dir():
        return dataset_path, None
    if dataset_path.suffix.lower() != ".zip":
        raise ValueError("Dataset must be an extracted directory or a training-data ZIP archive.")
    temporary_directory = tempfile.TemporaryDirectory(prefix="dysarthria-asr-benchmark-")
    root = Path(temporary_directory.name)
    extract_archive(dataset_path, root)
    return root, temporary_directory


def load_dataset(root: Path) -> list[DatasetItem]:
    labels_path = root / "training-labels.csv"
    if not labels_path.is_file():
        raise ValueError("Dataset does not contain training-labels.csv.")

    items: list[DatasetItem] = []
    with labels_path.open(newline="", encoding="utf-8") as labels_file:
        for row in csv.DictReader(labels_file):
            transcript = (row.get("transcript") or "").strip()
            if not transcript:
                continue
            audio_file = row.get("audio_file") or ""
            audio_path = (root / audio_file).resolve()
            try:
                audio_path.relative_to(root.resolve())
            except ValueError as error:
                raise ValueError(f"Label has an unsafe audio path: {audio_file}") from error
            if not audio_path.is_file():
                raise ValueError(f"Audio file is missing: {audio_file}")
            items.append(
                DatasetItem(
                    audio_id=row.get("audio_id") or audio_path.stem,
                    audio_file=audio_file,
                    source=row.get("source") or "",
                    transcript=transcript,
                )
            )
    if not items:
        raise ValueError("Dataset has no labeled audio with a transcript.")
    return items


def parse_model(model_spec: str) -> tuple[str, str]:
    label, separator, model_source = model_spec.partition("=")
    if separator:
        if not label or not model_source:
            raise ValueError("Model must be a model name or label=model-name.")
        return label, model_source
    return model_spec, model_spec


def transcribe(model, audio_path: Path, language: str, beam_size: int, vad_filter: bool) -> str:
    segments, _ = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=vad_filter,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def benchmark_model(model_label: str, model, items: list[DatasetItem], arguments) -> tuple[list[dict], dict]:
    details: list[dict] = []
    total_word_errors = total_reference_words = 0
    total_character_errors = total_reference_characters = 0
    total_seconds = 0.0
    failed_clips = 0

    for item in items:
        started_at = time.perf_counter()
        try:
            prediction = transcribe(
                model,
                arguments.dataset_root / item.audio_file,
                arguments.language,
                arguments.beam_size,
                arguments.vad_filter,
            )
            elapsed = time.perf_counter() - started_at
            word_errors, reference_words = word_metrics(item.transcript, prediction)
            character_errors, reference_characters = character_metrics(item.transcript, prediction)
            total_word_errors += word_errors
            total_reference_words += reference_words
            total_character_errors += character_errors
            total_reference_characters += reference_characters
            total_seconds += elapsed
            details.append(
                {
                    "model": model_label,
                    "audio_id": item.audio_id,
                    "audio_file": item.audio_file,
                    "source": item.source,
                    "expected_transcript": item.transcript,
                    "predicted_transcript": prediction,
                    "word_errors": word_errors,
                    "reference_words": reference_words,
                    "word_error_rate": word_errors / reference_words if reference_words else "",
                    "character_errors": character_errors,
                    "reference_characters": reference_characters,
                    "character_error_rate": character_errors / reference_characters if reference_characters else "",
                    "transcription_seconds": f"{elapsed:.3f}",
                    "error": "",
                }
            )
        except Exception as error:
            failed_clips += 1
            details.append(
                {
                    "model": model_label,
                    "audio_id": item.audio_id,
                    "audio_file": item.audio_file,
                    "source": item.source,
                    "expected_transcript": item.transcript,
                    "predicted_transcript": "",
                    "word_errors": "",
                    "reference_words": "",
                    "word_error_rate": "",
                    "character_errors": "",
                    "reference_characters": "",
                    "character_error_rate": "",
                    "transcription_seconds": "",
                    "error": str(error),
                }
            )

    return details, {
        "model": model_label,
        "successful_clips": len(items) - failed_clips,
        "failed_clips": failed_clips,
        "reference_words": total_reference_words,
        "word_errors": total_word_errors,
        "word_error_rate": total_word_errors / total_reference_words if total_reference_words else "",
        "reference_characters": total_reference_characters,
        "character_errors": total_character_errors,
        "character_error_rate": total_character_errors / total_reference_characters if total_reference_characters else "",
        "total_transcription_seconds": f"{total_seconds:.3f}",
    }


def arguments_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare Whisper models on a labeled dysarthria-ASR export.")
    parser.add_argument("dataset", type=Path, help="Training-data ZIP or extracted training-data directory.")
    parser.add_argument("--model", action="append", required=True, help="Whisper model name, path, or label=model-name. Repeat for each model.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/asr-benchmark"), help="Directory for detail and summary CSV files.")
    parser.add_argument("--language", default="de", help="Whisper language code. Default: de.")
    parser.add_argument("--beam-size", type=int, default=5, help="Whisper beam size. Default: 5.")
    parser.add_argument("--device", default="cpu", help="faster-whisper device. Default: cpu.")
    parser.add_argument("--compute-type", default="int8", help="faster-whisper compute type. Default: int8.")
    parser.add_argument("--vad-filter", action=argparse.BooleanOptionalAction, default=True, help="Enable voice activity filtering. Default: enabled.")
    return parser


def main() -> int:
    arguments = arguments_parser().parse_args()
    try:
        dataset_root, temporary_directory = resolve_dataset_root(arguments.dataset)
        arguments.dataset_root = dataset_root
        items = load_dataset(dataset_root)
        arguments.output_dir.mkdir(parents=True, exist_ok=True)

        from faster_whisper import WhisperModel

        all_details: list[dict] = []
        summaries: list[dict] = []
        for model_spec in arguments.model:
            model_label, model_source = parse_model(model_spec)
            print(f"Loading {model_label}: {model_source}", file=sys.stderr)
            model = WhisperModel(
                model_source,
                device=arguments.device,
                compute_type=arguments.compute_type,
            )
            details, summary = benchmark_model(model_label, model, items, arguments)
            all_details.extend(details)
            summaries.append(summary)
            print(f"Finished {model_label}", file=sys.stderr)

        write_csv(arguments.output_dir / "details.csv", DETAIL_FIELDS, all_details)
        write_csv(arguments.output_dir / "summary.csv", SUMMARY_FIELDS, summaries)
        print(f"Wrote results to {arguments.output_dir}", file=sys.stderr)
        return 0
    except (ValueError, zipfile.BadZipFile) as error:
        print(f"Benchmark failed: {error}", file=sys.stderr)
        return 2
    finally:
        if "temporary_directory" in locals() and temporary_directory is not None:
            temporary_directory.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
