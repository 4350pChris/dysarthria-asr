from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from benchmark_asr import DatasetItem, load_dataset, metrics, select_split


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark NVIDIA Parakeet on labeled audio clips.")
    parser.add_argument("dataset", type=Path, help="Directory with training-labels.csv and data/audio files.")
    parser.add_argument("--model", default="primeline/parakeet-primeline")
    parser.add_argument("--model-file", default="2_95_WER.nemo", help="Model file in the Hugging Face repository.")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/reports/parakeet-benchmark"))
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    parser.add_argument("--split", type=Path, help="Optional split.csv file. Benchmarks its evaluation clips by default.")
    parser.add_argument("--split-name", default="evaluation")
    arguments = parser.parse_args()

    import nemo.collections.asr as nemo_asr

    root = arguments.dataset.resolve()
    items: list[DatasetItem] = load_dataset(root)
    if arguments.split:
        items = select_split(items, arguments.split, arguments.split_name)
    arguments.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {arguments.model}", file=sys.stderr)
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download(arguments.model, arguments.model_file)
    model = nemo_asr.models.ASRModel.restore_from(model_path, map_location=arguments.device)
    details: list[dict[str, str | int | float]] = []
    total_word_errors = total_words = total_character_errors = total_characters = 0
    total_seconds = 0.0
    for item in items:
        started = time.perf_counter()
        result = model.transcribe([str(root / item.audio_file)], batch_size=1)[0]
        prediction = result.text if hasattr(result, "text") else str(result)
        elapsed = time.perf_counter() - started
        word_errors, word_count, character_errors, character_count = metrics(item.transcript, prediction)
        total_word_errors += word_errors
        total_words += word_count
        total_character_errors += character_errors
        total_characters += character_count
        total_seconds += elapsed
        details.append({"model": arguments.model, "audio_id": item.audio_id, "audio_file": item.audio_file, "expected_transcript": item.transcript, "predicted_transcript": prediction, "word_error_rate": word_errors / word_count, "character_error_rate": character_errors / character_count, "transcription_seconds": f"{elapsed:.3f}"})

    summary = {
        "model": arguments.model,
        "clips": len(items),
        "word_error_rate": total_word_errors / total_words,
        "character_error_rate": total_character_errors / total_characters,
        "total_transcription_seconds": f"{total_seconds:.3f}",
    }
    for path, rows in ((arguments.output_dir / "details.csv", details), (arguments.output_dir / "summary.csv", [summary])):
        with path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Wrote results to {arguments.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
