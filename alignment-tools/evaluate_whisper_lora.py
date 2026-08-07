from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from train_whisper_lora import Item, WhisperDataset, evaluate


def evaluation_items(dataset_dir: Path, split_path: Path) -> list[Item]:
    with split_path.open(newline="", encoding="utf-8") as input_file:
        return [
            Item(dataset_dir / row["audio_file"], row["transcript"], row["audio_id"])
            for row in csv.DictReader(input_file)
            if row["split"] == "evaluation"
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a saved Whisper LoRA adapter on its held-out split.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("training_output", type=Path)
    parser.add_argument("--base", action="store_true", help="Evaluate the unchanged base model on the same split.")
    arguments = parser.parse_args()

    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS is not available.")
    adapter_path = arguments.training_output / "adapter"
    split_path = arguments.training_output / "split.csv"
    if not split_path.is_file() or (not arguments.base and not adapter_path.is_dir()):
        raise ValueError("Training output must contain split.csv and, for adapter evaluation, adapter/.")
    model_name = "openai/whisper-large-v3-turbo"
    processor = WhisperProcessor.from_pretrained(adapter_path)
    model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.bfloat16)
    if not arguments.base:
        model.load_adapter(adapter_path)
    model.generation_config.language = "german"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.to("mps")
    items = evaluation_items(arguments.dataset.resolve(), split_path)
    word_error_rate = evaluate(model, processor, WhisperDataset(items, processor), "mps")
    metrics_path = arguments.training_output / ("base-metrics.json" if arguments.base else "metrics.json")
    metrics_path.write_text(json.dumps({"evaluation_word_error_rate": word_error_rate, "evaluation_clips": len(items)}, indent=2) + "\n")
    print(f"Evaluation WER: {word_error_rate:.3%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
