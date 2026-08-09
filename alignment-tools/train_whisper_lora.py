from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
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
    groups: dict[tuple[str, ...], list[Item]] = {}
    for item in items:
        groups.setdefault(tuple(normalized_words(item.transcript)), []).append(item)
    group_keys = list(groups)
    random.Random(42).shuffle(group_keys)
    evaluation_count = max(1, round(len(items) * evaluation_fraction))
    evaluation_keys: set[tuple[str, ...]] = set()
    evaluation_size = 0
    for key in group_keys:
        if evaluation_size >= evaluation_count:
            break
        evaluation_keys.add(key)
        evaluation_size += len(groups[key])
    evaluation_items = [item for item in items if tuple(normalized_words(item.transcript)) in evaluation_keys]
    train_items = [item for item in items if tuple(normalized_words(item.transcript)) not in evaluation_keys]
    return train_items, evaluation_items


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
        return {"input_features": features, "transcript": item.transcript, "item": item}


@dataclass
class Collator:
    processor: WhisperProcessor

    def __call__(self, features: list[dict]) -> dict[str, torch.Tensor]:
        input_features = self.processor.feature_extractor.pad(
            [{"input_features": feature["input_features"]} for feature in features], return_tensors="pt"
        )
        input_features["input_features"].requires_grad_(True)
        labels = self.processor.tokenizer(
            [feature["transcript"] for feature in features],
            padding=True,
            return_tensors="pt",
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


def save_best_adapter(trainer: Seq2SeqTrainer, output_dir: Path, processor: WhisperProcessor) -> None:
    adapter_dir = output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_name = trainer.state.best_model_checkpoint
    if checkpoint_name:
        checkpoint = Path(checkpoint_name)
        for name in ("adapter_config.json", "adapter_model.safetensors"):
            source = checkpoint / name
            if not source.is_file():
                raise FileNotFoundError(source)
            shutil.copy2(source, adapter_dir / name)
    else:
        trainer.model.save_pretrained(adapter_dir)
    processor.save_pretrained(adapter_dir)


def evaluate(model, processor: WhisperProcessor, dataset: WhisperDataset, device: str) -> float:
    errors = total_words = 0
    model.eval()
    with torch.inference_mode():
        for index in range(len(dataset)):
            feature = dataset[index]
            input_features = torch.tensor(feature["input_features"]).unsqueeze(0).to(
                device=device, dtype=next(model.parameters()).dtype
            )
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
    parser.add_argument("--model-name", default="openai/whisper-large-v3-turbo")
    parser.add_argument("--epochs", type=float, default=12)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--evaluation-fraction", type=float, default=0.2)
    parser.add_argument("--precision", choices=["bf16", "fp32"], default="bf16")
    parser.add_argument("--max-steps", type=int, default=-1, help="Stop after this many optimizer updates. Default: all.")
    parser.add_argument("--only-audio-id", help="Train only this audio ID. Diagnostic use only.")
    parser.add_argument("--skip-trainer-evaluation", action="store_true")
    parser.add_argument("--skip-final-evaluation", action="store_true")
    arguments = parser.parse_args()

    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple MPS is not available.")
    checkpoints = arguments.output_dir / "checkpoints"
    if (arguments.output_dir / "adapter").exists() or any(checkpoints.glob("checkpoint-*")):
        raise FileExistsError(f"Training output already exists: {arguments.output_dir}")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = arguments.dataset.resolve()
    train_items, evaluation_items = split_items(read_items(dataset_dir), arguments.evaluation_fraction)
    if arguments.only_audio_id:
        train_items = [item for item in train_items if item.audio_id == arguments.only_audio_id]
        if not train_items:
            raise ValueError(f"Audio ID is not in the training split: {arguments.only_audio_id}")
    write_split(arguments.output_dir / "split.csv", train_items, evaluation_items, dataset_dir)

    model_name = arguments.model_name
    processor = WhisperProcessor.from_pretrained(model_name, language="German", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.bfloat16 if arguments.precision == "bf16" else torch.float32)
    model.generation_config.language = "german"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.use_cache = False
    model.add_adapter(LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"]))
    model.enable_input_require_grads()
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    total_parameters = sum(parameter.numel() for parameter in model.parameters())
    print(f"Trainable parameters: {trainable_parameters:,} / {total_parameters:,}")

    evaluation_enabled = not arguments.skip_trainer_evaluation
    training_arguments = Seq2SeqTrainingArguments(
        output_dir=str(arguments.output_dir / "checkpoints"),
        per_device_train_batch_size=arguments.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=arguments.gradient_accumulation_steps,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        learning_rate=arguments.learning_rate,
        warmup_ratio=arguments.warmup_ratio,
        num_train_epochs=arguments.epochs,
        max_steps=arguments.max_steps,
        eval_strategy="epoch" if evaluation_enabled else "no",
        save_strategy="epoch" if evaluation_enabled else "no",
        load_best_model_at_end=False,
        metric_for_best_model="eval_loss" if evaluation_enabled else None,
        greater_is_better=False if evaluation_enabled else None,
        save_total_limit=2 if evaluation_enabled else None,
        logging_steps=1,
        report_to="none",
        remove_unused_columns=False,
        bf16=arguments.precision == "bf16",
        dataloader_num_workers=0,
        dataloader_pin_memory=False,
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
    save_best_adapter(trainer, arguments.output_dir, processor)
    if arguments.skip_final_evaluation:
        return 0
    word_error_rate = evaluate(model, processor, WhisperDataset(evaluation_items, processor), "mps")
    (arguments.output_dir / "metrics.json").write_text(
        json.dumps({"evaluation_word_error_rate": word_error_rate, "train_clips": len(train_items), "evaluation_clips": len(evaluation_items)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Evaluation WER: {word_error_rate:.3%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
