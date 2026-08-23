from __future__ import annotations

import csv
import json
import re
import shutil
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import modal


PROJECT_DIR = Path(__file__).parent
DATASET_DIR = PROJECT_DIR / "data/datasets/combined-v3"
SPLIT_PATH = PROJECT_DIR / "runs/training/whisper-large-v3-turbo-lora-combined-v3/split.csv"
REMOTE_DATASET_DIR = Path("/data")
MODEL_NAME = "openai/whisper-large-v3-turbo"
OUTPUT_VOLUME_NAME = "dysarthria-asr-training-results"

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.10")
    .entrypoint([])
    .uv_pip_install(
        "torch==2.7.1",
        "transformers==4.57.6",
        "peft==0.19.1",
        "accelerate>=1.0",
        "soundfile",
        extra_index_url="https://download.pytorch.org/whl/cu128",
        extra_options="--index-strategy unsafe-best-match",
    )
    .add_local_dir(DATASET_DIR, remote_path=str(REMOTE_DATASET_DIR))
    .add_local_file(SPLIT_PATH, remote_path="/split.csv")
)
app = modal.App("dysarthria-asr-whisper-lora", image=image)
output_volume = modal.Volume.from_name(OUTPUT_VOLUME_NAME, create_if_missing=True)


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


def read_split() -> tuple[list[Item], list[Item]]:
    with Path("/split.csv").open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    items_by_split: dict[str, list[Item]] = {"train": [], "evaluation": []}
    for row in rows:
        split = row["split"]
        if split == "excluded":
            continue
        if split not in items_by_split:
            raise ValueError(f"Unknown split: {split}")
        items_by_split[split].append(
            Item(REMOTE_DATASET_DIR / row["audio_file"], row["transcript"].strip(), row["audio_id"])
        )
    if not items_by_split["train"] or not items_by_split["evaluation"]:
        raise ValueError("Split must contain training and evaluation clips.")
    return items_by_split["train"], items_by_split["evaluation"]


@app.function(gpu="L4", timeout=2 * 60 * 60, retries=0, volumes={"/output": output_volume})
def train(
    run_name: str = "whisper-large-v3-turbo-lora-combined-v3",
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

    if not run_name or "/" in run_name or "\\" in run_name:
        raise ValueError("run_name must be a single directory name.")
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

    def evaluate(model, processor: WhisperProcessor, dataset: WhisperDataset) -> float:
        errors = total_words = 0
        model.eval()
        with torch.inference_mode():
            for index in range(len(dataset)):
                feature = dataset[index]
                input_features = torch.tensor(feature["input_features"]).unsqueeze(0).to(
                    device="cuda", dtype=next(model.parameters()).dtype
                )
                tokens = model.generate(input_features=input_features, max_new_tokens=128)
                prediction = processor.tokenizer.batch_decode(tokens, skip_special_tokens=True)[0]
                reference_words = normalized_words(feature["item"].transcript)
                errors += edit_distance(reference_words, normalized_words(prediction))
                total_words += len(reference_words)
        return errors / total_words

    train_items, evaluation_items = read_split()
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language="German", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME, torch_dtype=torch.bfloat16)
    model.generation_config.language = "german"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.use_cache = False
    model.add_adapter(LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"]))
    model.enable_input_require_grads()

    output_dir = Path("/output") / run_name
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    training_arguments = Seq2SeqTrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
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
        eval_dataset=WhisperDataset(evaluation_items, processor),
        data_collator=Collator(processor),
        processing_class=processor.feature_extractor,
    )
    started = time.perf_counter()
    trainer.train()
    adapter_dir = output_dir / "adapter"
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
        "evaluation_clips": len(evaluation_items),
        "evaluation_word_error_rate": evaluate(model, processor, WhisperDataset(evaluation_items, processor)),
        "training_seconds": time.perf_counter() - started,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    shutil.copy2("/split.csv", output_dir / "split.csv")
    output_volume.commit()
    return metrics


@app.local_entrypoint()
def main(
    run_name: str = "whisper-large-v3-turbo-lora-combined-v3",
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
