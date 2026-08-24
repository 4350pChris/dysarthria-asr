from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import modal
from modal_training import OUTPUT_VOLUME, REMOTE_DATASET_DIR, output_dir, read_split_rows, save_run, training_image


MODEL_NAME = "openai/whisper-large-v3-turbo"

image = training_image("torch==2.7.1", "transformers==4.57.6", "peft==0.19.1", "accelerate>=1.0", "soundfile")
app = modal.App("dysarthria-asr-whisper-lora", image=image)


@dataclass(frozen=True)
class Item:
    audio_path: Path
    transcript: str
    audio_id: str


def read_split() -> tuple[list[Item], list[Item]]:
    rows = read_split_rows()
    items_by_split: dict[str, list[Item]] = {"train": [], "validation": []}
    for row in rows:
        split = row["split"]
        if split == "test":
            continue
        if split not in items_by_split:
            raise ValueError(f"Unknown split: {split}")
        items_by_split[split].append(
            Item(REMOTE_DATASET_DIR / row["audio_file"], row["transcript"].strip(), row["audio_id"])
        )
    if not items_by_split["train"] or not items_by_split["validation"]:
        raise ValueError("Split must contain training and validation clips.")
    return items_by_split["train"], items_by_split["validation"]


@app.function(gpu="L4", timeout=2 * 60 * 60, retries=0, volumes={"/output": OUTPUT_VOLUME})
def train(
    run_name: str = "whisper-large-v3-turbo-lora-experiment",
    epochs: float = 12,
    learning_rate: float = 5e-5,
    batch_size: int = 2,
    gradient_accumulation_steps: int = 4,
) -> dict[str, int | float | str]:
    import soundfile as sf
    import torch
    from peft import LoraConfig
    from torch.utils.data import Dataset
    from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration, WhisperProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available.")

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
            batch = self.processor.feature_extractor.pad(
                [{"input_features": feature["input_features"]} for feature in features], return_tensors="pt"
            )
            batch["input_features"].requires_grad_(True)
            labels = self.processor.tokenizer(
                [feature["transcript"] for feature in features], padding=True, return_tensors="pt"
            )
            batch["labels"] = labels["input_ids"].masked_fill(labels.attention_mask.ne(1), -100)
            return batch

    train_items, validation_items = read_split()
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language="German", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME, torch_dtype=torch.bfloat16)
    model.generation_config.language = "german"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.use_cache = False
    model.add_adapter(LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"]))
    model.enable_input_require_grads()

    run_dir = output_dir(run_name)
    training_arguments = Seq2SeqTrainingArguments(
        output_dir=str(run_dir / "checkpoints"),
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=gradient_accumulation_steps,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        learning_rate=learning_rate,
        warmup_ratio=0.1,
        num_train_epochs=epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        logging_steps=1,
        report_to="none",
        remove_unused_columns=False,
        bf16=True,
        dataloader_num_workers=2,
        dataloader_pin_memory=True,
        optim="adamw_torch",
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_arguments,
        train_dataset=WhisperDataset(train_items, processor),
        eval_dataset=WhisperDataset(validation_items, processor),
        data_collator=Collator(processor),
        processing_class=processor.feature_extractor,
    )
    started = time.perf_counter()
    trainer.train()
    adapter_dir = run_dir / "adapter"
    adapter_dir.mkdir()
    checkpoint_name = trainer.state.best_model_checkpoint
    if checkpoint_name:
        checkpoint = Path(checkpoint_name)
        for name in ("adapter_config.json", "adapter_model.safetensors"):
            shutil.copy2(checkpoint / name, adapter_dir / name)
    else:
        trainer.model.save_pretrained(adapter_dir)
    processor.save_pretrained(adapter_dir)

    metrics = {
        "model": MODEL_NAME,
        "adapter": "lora-q-v-r8",
        "epochs": epochs,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "train_clips": len(train_items),
        "validation_clips": len(validation_items),
        "best_validation_loss": trainer.state.best_metric,
        "training_seconds": time.perf_counter() - started,
    }
    save_run(run_dir, metrics)
    return metrics


@app.local_entrypoint()
def main(
    run_name: str = "whisper-large-v3-turbo-lora-experiment",
    epochs: float = 12,
    learning_rate: float = 5e-5,
    batch_size: int = 2,
    gradient_accumulation_steps: int = 4,
) -> None:
    print(
        json.dumps(
            train.remote(
                run_name=run_name,
                epochs=epochs,
                learning_rate=learning_rate,
                batch_size=batch_size,
                gradient_accumulation_steps=gradient_accumulation_steps,
            ),
            indent=2,
        )
    )
