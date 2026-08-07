from __future__ import annotations

import argparse
import csv
import json
import random
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from peft import LoraConfig
from torch.utils.data import Dataset
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration, WhisperProcessor


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[\w]+", unicodedata.normalize("NFKC", text).casefold())


def edit_distance(reference: list[str], prediction: list[str]) -> int:
    previous = list(range(len(prediction) + 1))
    for reference_index, reference_word in enumerate(reference, start=1):
        current = [reference_index]
        for prediction_index, prediction_word in enumerate(prediction, start=1):
            current.append(
                min(
                    previous[prediction_index - 1] + (reference_word != prediction_word),
                    current[prediction_index - 1] + 1,
                    previous[prediction_index] + 1,
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class Item:
    audio_path: Path
    transcript: str
    audio_id: str


def read_items(dataset_dir: Path) -> list[Item]:
    labels_path = dataset_dir / "training-labels.csv"
    with labels_path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    items = [
        Item(dataset_dir / row["audio_file"], row["transcript"].strip(), row["audio_id"])
        for row in rows
        if row.get("transcript", "").strip()
    ]
    if len(items) < 10:
        raise ValueError("Need at least ten labeled clips for a train and evaluation split.")
    return items


def split_items(items: list[Item], evaluation_fraction: float) -> tuple[list[Item], list[Item]]:
    shuffled = items.copy()
    random.Random(42).shuffle(shuffled)
    evaluation_count = max(1, round(len(shuffled) * evaluation_fraction))
    return shuffled[evaluation_count:], shuffled[:evaluation_count]


class WhisperDataset(Dataset):
    def __init__(self, items: list[Item], processor: WhisperProcessor):
        self.items = items
        self.processor = processor

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict:
        item = self.items[index]
        audio, sample_rate = sf.read(item.audio_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sample_rate != 16_000:
            raise ValueError(f"Expected 16 kHz audio: {item.audio_path}")
        features = self.processor.feature_extractor(audio, sampling_rate=sample_rate).input_features[0]
        labels = self.processor.tokenizer(item.transcript).input_ids
        return {"input_features": features, "labels": labels, "item": item}


@dataclass
class Collator:
    processor: WhisperProcessor

    def __call__(self, features: list[dict]) -> dict[str, torch.Tensor]:
        input_features = self.processor.feature_extractor.pad(
            [{"input_features": feature["input_features"]} for feature in features], return_tensors="pt"
        )
        labels = self.processor.tokenizer.pad(
            [{"input_ids": feature["labels"]} for feature in features], return_tensors="pt"
        )
        input_features["labels"] = labels["input_ids"].masked_fill(labels.attention_mask.ne(1), -100)
        return input_features


def write_split(path: Path, train_items: list[Item], evaluation_items: list[Item], dataset_dir: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["audio_id", "split", "audio_file", "transcript"])
        writer.writeheader()
        for split, items in (("train", train_items), ("evaluation", evaluation_items)):
            for item in items:
                writer.writerow(
                    {
                        "audio_id": item.audio_id,
                        "split": split,
                        "audio_file": item.audio_path.relative_to(dataset_dir).as_posix(),
                        "transcript": item.transcript,
                    }
                )


def evaluate(model, processor: WhisperProcessor, dataset: WhisperDataset, device: str) -> float:
    errors = total_words = 0
    model.eval()
    with torch.inference_mode():
        for index in range(len(dataset)):
            feature = dataset[index]
            input_features = torch.tensor(feature["input_features"]).unsqueeze(0).to(device)
            tokens = model.generate(input_features=input_features, max_new_tokens=128)
            prediction = processor.tokenizer.batch_decode(tokens, skip_special_tokens=True)[0]
            reference_words = normalized_words(feature["item"].transcript)
            errors += edit_distance(reference_words, normalized_words(prediction))
            total_words += len(reference_words)
    return errors / total_words


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune Whisper large-v3-turbo with LoRA on local Apple Silicon.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/whisper-large-v3-turbo-lora"))
    parser.add_argument("--epochs", type=float, default=3)
    parser.add_argument("--evaluation-fraction", type=float, default=0.2)
    parser.add_argument("--precision", choices=["bf16", "fp32"], default="bf16")
    arguments = parser.parse_args()

    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS is not available.")
    checkpoints = arguments.output_dir / "checkpoints"
    if (arguments.output_dir / "adapter").exists() or any(checkpoints.glob("checkpoint-*")):
        raise FileExistsError(f"Training output already exists: {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = arguments.dataset.resolve()
    train_items, evaluation_items = split_items(read_items(dataset_dir), arguments.evaluation_fraction)
    write_split(arguments.output_dir / "split.csv", train_items, evaluation_items, dataset_dir)

    model_name = "openai/whisper-large-v3-turbo"
    processor = WhisperProcessor.from_pretrained(model_name, language="German", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.bfloat16 if arguments.precision == "bf16" else torch.float32)
    model.generation_config.language = "german"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.use_cache = False
    model.add_adapter(LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"]))
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    total_parameters = sum(parameter.numel() for parameter in model.parameters())
    print(f"Trainable parameters: {trainable_parameters:,} / {total_parameters:,}")

    training_arguments = Seq2SeqTrainingArguments(
        output_dir=str(arguments.output_dir / "checkpoints"),
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        gradient_checkpointing=False,
        learning_rate=1e-4,
        num_train_epochs=arguments.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=1,
        report_to="none",
        remove_unused_columns=False,
        bf16=arguments.precision == "bf16",
        dataloader_num_workers=0,
        optim="adamw_torch",
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_arguments,
        train_dataset=WhisperDataset(train_items, processor),
        eval_dataset=WhisperDataset(evaluation_items, processor),
        data_collator=Collator(processor),
        processing_class=processor.feature_extractor,
    )
    trainer.train()
    model.save_pretrained(arguments.output_dir / "adapter")
    processor.save_pretrained(arguments.output_dir / "adapter")
    word_error_rate = evaluate(model, processor, WhisperDataset(evaluation_items, processor), "mps")
    (arguments.output_dir / "metrics.json").write_text(
        json.dumps({"evaluation_word_error_rate": word_error_rate, "train_clips": len(train_items), "evaluation_clips": len(evaluation_items)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Evaluation WER: {word_error_rate:.3%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
