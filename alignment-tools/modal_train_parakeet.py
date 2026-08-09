from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path

import modal


PROJECT_DIR = Path(__file__).parent
DATASET_DIR = PROJECT_DIR / "data/datasets/combined-v2"
SPLIT_PATH = PROJECT_DIR / "runs/training/whisper-large-v3-turbo-lora-combined-v2/split.csv"
REMOTE_DATASET_DIR = Path("/data")
REMOTE_OUTPUT_DIR = Path("/output/primeline-parakeet-joint-only-v1")
MODEL_ID = "primeline/parakeet-primeline"
MODEL_FILE = "2_95_WER.nemo"

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.10")
    .entrypoint([])
    .uv_pip_install(
        "torch==2.7.1",
        "cuda-python==12.8.0",
        "numba==0.61.2",
        "nemo_toolkit[asr]==3.0.0",
        "soundfile",
        extra_index_url="https://download.pytorch.org/whl/cu128",
        extra_options="--index-strategy unsafe-best-match",
    )
    .env({"NUMBA_CUDA_USE_NVIDIA_BINDING": "1"})
    .add_local_dir(DATASET_DIR, remote_path=str(REMOTE_DATASET_DIR))
    .add_local_file(SPLIT_PATH, remote_path="/split.csv")
)
app = modal.App("dysarthria-asr-parakeet-finetune", image=image)
output_volume = modal.Volume.from_name("dysarthria-asr-training-results", create_if_missing=True)


def normalize(text: str) -> list[str]:
    return re.findall(r"[\w]+", unicodedata.normalize("NFKC", text).casefold())


def edit_distance(reference: list[str], prediction: list[str]) -> int:
    previous = list(range(len(prediction) + 1))
    for reference_index, reference_token in enumerate(reference, start=1):
        current = [reference_index]
        for prediction_index, prediction_token in enumerate(prediction, start=1):
            current.append(min(previous[prediction_index - 1] + (reference_token != prediction_token), current[prediction_index - 1] + 1, previous[prediction_index] + 1))
        previous = current
    return previous[-1]


@app.function(gpu="L4", timeout=2 * 60 * 60, retries=0, volumes={"/output": output_volume})
def train(epochs: int = 20, learning_rate: float = 1e-5) -> dict[str, int | float | str]:
    import lightning.pytorch as pl
    from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
    import soundfile
    import torch
    from huggingface_hub import hf_hub_download
    from nemo.collections.asr.models import ASRModel
    from omegaconf import OmegaConf

    split_rows = list(csv.DictReader(Path("/split.csv").open(newline="", encoding="utf-8")))
    candidate_rows = [row for row in split_rows if row["split"] == "train"]
    candidate_rows.sort(key=lambda row: hashlib.sha256(f"parakeet-joint-only-v1:{row['audio_id']}".encode()).hexdigest())
    validation_rows = candidate_rows[:19]
    training_rows = candidate_rows[19:]
    test_rows = [row for row in split_rows if row["split"] == "evaluation"]

    def write_manifest(name: str, rows: list[dict[str, str]]) -> Path:
        manifest_path = Path("/tmp") / f"{name}.jsonl"
        with manifest_path.open("w", encoding="utf-8") as output:
            for row in rows:
                audio_path = REMOTE_DATASET_DIR / row["audio_file"]
                info = soundfile.info(audio_path)
                output.write(json.dumps({"audio_filepath": str(audio_path), "duration": info.frames / info.samplerate, "text": row["transcript"]}, ensure_ascii=False) + "\n")
        return manifest_path

    train_manifest = write_manifest("train", training_rows)
    validation_manifest = write_manifest("validation", validation_rows)
    model_path = hf_hub_download(MODEL_ID, MODEL_FILE)
    model = ASRModel.restore_from(model_path)
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.joint.parameters():
        parameter.requires_grad = True
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)

    train_config = OmegaConf.create({"manifest_filepath": str(train_manifest), "sample_rate": 16000, "batch_size": 2, "shuffle": True, "num_workers": 2, "pin_memory": True, "max_duration": 30.0, "min_duration": 0.1, "use_lhotse": False})
    validation_config = OmegaConf.create({"manifest_filepath": str(validation_manifest), "sample_rate": 16000, "batch_size": 1, "shuffle": False, "num_workers": 2, "pin_memory": True, "max_duration": 30.0, "min_duration": 0.1, "use_lhotse": False})
    model.setup_training_data(train_config)
    model.setup_validation_data(validation_config)
    model.setup_optimization({"name": "adamw", "lr": learning_rate, "weight_decay": 0.01})
    checkpoint = ModelCheckpoint(dirpath="/tmp/checkpoints", monitor="val_wer", mode="min", save_top_k=1)
    early_stopping = EarlyStopping(monitor="val_wer", mode="min", patience=3)
    trainer = pl.Trainer(accelerator="gpu", devices=1, max_epochs=epochs, precision="16-mixed", logger=False, callbacks=[checkpoint, early_stopping], enable_model_summary=False, log_every_n_steps=1, num_sanity_val_steps=0)
    started = time.perf_counter()
    trainer.fit(model)
    training_seconds = time.perf_counter() - started
    model.load_state_dict(torch.load(checkpoint.best_model_path, map_location="cpu", weights_only=False)["state_dict"])

    model.eval()
    total_errors = total_words = 0
    with torch.inference_mode():
        for row in test_rows:
            result = model.transcribe([str(REMOTE_DATASET_DIR / row["audio_file"])], batch_size=1)[0]
            prediction = result.text if hasattr(result, "text") else str(result)
            reference_words = normalize(row["transcript"])
            total_errors += edit_distance(reference_words, normalize(prediction))
            total_words += len(reference_words)
    metrics = {"model": MODEL_ID, "adaptation": "joint_only", "max_epochs": epochs, "completed_epochs": trainer.current_epoch + 1, "learning_rate": learning_rate, "trainable_parameters": trainable_parameters, "train_clips": len(training_rows), "validation_clips": len(validation_rows), "test_clips": len(test_rows), "best_validation_word_error_rate": float(checkpoint.best_model_score), "test_word_error_rate": total_errors / total_words, "training_seconds": training_seconds}
    REMOTE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (REMOTE_OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    model.save_to(REMOTE_OUTPUT_DIR / "model.nemo")
    output_volume.commit()
    return metrics


@app.local_entrypoint()
def main(epochs: int = 20, learning_rate: float = 1e-5) -> None:
    print(json.dumps(train.remote(epochs=epochs, learning_rate=learning_rate), indent=2))
