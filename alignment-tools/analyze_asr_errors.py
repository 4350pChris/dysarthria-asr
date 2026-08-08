from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


def words(text: str) -> list[str]:
    """Return case- and punctuation-insensitive words."""
    return re.findall(r"[\w]+", unicodedata.normalize("NFKC", text).casefold())


@dataclass(frozen=True)
class Edit:
    kind: str
    reference: str
    prediction: str


def align(reference: list[str], prediction: list[str]) -> list[Edit]:
    """Return one minimum-edit alignment from reference words to predicted words."""
    rows, columns = len(reference), len(prediction)
    costs = [[0] * (columns + 1) for _ in range(rows + 1)]
    for row in range(1, rows + 1):
        costs[row][0] = row
    for column in range(1, columns + 1):
        costs[0][column] = column
    for row in range(1, rows + 1):
        for column in range(1, columns + 1):
            costs[row][column] = min(
                costs[row - 1][column] + 1,
                costs[row][column - 1] + 1,
                costs[row - 1][column - 1] + (reference[row - 1] != prediction[column - 1]),
            )

    edits: list[Edit] = []
    row, column = rows, columns
    while row or column:
        if row and column and reference[row - 1] == prediction[column - 1] and costs[row][column] == costs[row - 1][column - 1]:
            edits.append(Edit("correct", reference[row - 1], prediction[column - 1]))
            row, column = row - 1, column - 1
        elif row and column and costs[row][column] == costs[row - 1][column - 1] + 1:
            edits.append(Edit("substitution", reference[row - 1], prediction[column - 1]))
            row, column = row - 1, column - 1
        elif row and costs[row][column] == costs[row - 1][column] + 1:
            edits.append(Edit("deletion", reference[row - 1], ""))
            row -= 1
        else:
            edits.append(Edit("insertion", "", prediction[column - 1]))
            column -= 1
    return list(reversed(edits))


def load_sources(dataset: Path) -> dict[str, str]:
    with (dataset / "training-labels.csv").open(newline="", encoding="utf-8") as input_file:
        return {row["audio_id"]: row.get("source", "") or "unknown" for row in csv.DictReader(input_file)}


def write_csv(path: Path, rows: list[dict[str, str | int | float]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create local word-error reports from benchmark details.csv.")
    parser.add_argument("dataset", type=Path, help="Directory with training-labels.csv.")
    parser.add_argument("details", type=Path, help="details.csv made by benchmark_asr.py.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/asr-error-analysis"))
    arguments = parser.parse_args()

    sources = load_sources(arguments.dataset.resolve())
    with arguments.details.open(newline="", encoding="utf-8") as input_file:
        benchmark_rows = list(csv.DictReader(input_file))
    if not benchmark_rows:
        raise ValueError("Benchmark details file has no rows.")

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    clips: list[dict[str, str | int | float]] = []
    error_counts: Counter[tuple[str, str, str, str]] = Counter()
    model_totals: dict[str, Counter[str]] = defaultdict(Counter)
    source_totals: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for benchmark in benchmark_rows:
        model = benchmark["model"]
        source = sources.get(benchmark["audio_id"], "unknown")
        alignment = align(words(benchmark["expected_transcript"]), words(benchmark["predicted_transcript"]))
        counts = Counter(edit.kind for edit in alignment)
        errors = counts["substitution"] + counts["deletion"] + counts["insertion"]
        reference_words = counts["correct"] + counts["substitution"] + counts["deletion"]
        for total in (model_totals[model], source_totals[(model, source)]):
            total.update({"clips": 1, "reference_words": reference_words, "substitutions": counts["substitution"], "deletions": counts["deletion"], "insertions": counts["insertion"]})
        for edit in alignment:
            if edit.kind != "correct":
                error_counts[(model, edit.kind, edit.reference, edit.prediction)] += 1
        clips.append(
            {
                "model": model,
                "source": source,
                "audio_id": benchmark["audio_id"],
                "audio_file": benchmark["audio_file"],
                "expected_transcript": benchmark["expected_transcript"],
                "predicted_transcript": benchmark["predicted_transcript"],
                "reference_words": reference_words,
                "substitutions": counts["substitution"],
                "deletions": counts["deletion"],
                "insertions": counts["insertion"],
                "word_errors": errors,
                "word_error_rate": errors / reference_words if reference_words else 0,
                "character_error_rate": benchmark["character_error_rate"],
                "transcription_seconds": benchmark["transcription_seconds"],
                "word_alignment": " | ".join(f"{edit.kind}: {edit.reference or '∅'} → {edit.prediction or '∅'}" for edit in alignment),
            }
        )

    clips.sort(key=lambda row: (str(row["model"]), -float(row["word_error_rate"]), -int(row["word_errors"]), str(row["audio_id"])))
    write_csv(arguments.output_dir / "clips.csv", clips, list(clips[0]))
    word_errors = [
        {"model": model, "error_type": kind, "expected_word": reference, "predicted_word": prediction, "count": count}
        for (model, kind, reference, prediction), count in error_counts.items()
    ]
    word_errors.sort(key=lambda row: (str(row["model"]), -int(row["count"]), str(row["error_type"]), str(row["expected_word"]), str(row["predicted_word"])))
    write_csv(arguments.output_dir / "word-errors.csv", word_errors, ["model", "error_type", "expected_word", "predicted_word", "count"])

    summary: list[dict[str, str | int | float]] = []
    for (model, source), total in sorted(source_totals.items()):
        errors = total["substitutions"] + total["deletions"] + total["insertions"]
        summary.append({"model": model, "source": source, **total, "word_errors": errors, "word_error_rate": errors / total["reference_words"]})
    write_csv(arguments.output_dir / "summary-by-source.csv", summary, ["model", "source", "clips", "reference_words", "substitutions", "deletions", "insertions", "word_errors", "word_error_rate"])

    lines = ["# ASR error analysis", "", "This report is local. Do not use these evaluation clips for training.", "", "## Results by model", ""]
    for model, total in sorted(model_totals.items()):
        errors = total["substitutions"] + total["deletions"] + total["insertions"]
        lines.append(f"- {model}: {errors}/{total['reference_words']} word errors ({errors / total['reference_words']:.1%}); {total['substitutions']} substitutions, {total['deletions']} deletions, {total['insertions']} insertions.")
    lines.extend(["", "## Review order", "", "Open `clips.csv`. It lists the highest-WER clips first for each model. Listen to the audio and check the reviewed text before you use an error pattern to plan new recordings.", "", "Open `word-errors.csv` to find repeated wrong-word patterns. These are word-level alignments; one uncertain phrase can appear as several edits."])
    (arguments.output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote error analysis to {arguments.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
