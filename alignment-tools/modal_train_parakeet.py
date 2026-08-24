from __future__ import annotations

import json
import time

import modal
from modal_training import OUTPUT_VOLUME, output_dir, read_training_rows, save_run, training_image, write_manifest


MODEL_ID = "primeline/parakeet-primeline"
MODEL_FILE = "2_95_WER.nemo"

image = training_image("torch==2.7.1", "cuda-python==12.8.0", "numba==0.61.2", "nemo_toolkit[asr]==3.0.0", "soundfile", env={"NUMBA_CUDA_USE_NVIDIA_BINDING": "1"})
app = modal.App("dysarthria-asr-parakeet-joint", image=image)


@app.function(gpu="L4", timeout=2 * 60 * 60, retries=0, volumes={"/output": OUTPUT_VOLUME})
def train(run_name: str = "parakeet-joint-experiment", epochs: int = 20, learning_rate: float = 1e-5) -> dict[str, object]:
    import lightning.pytorch as pl
    import soundfile
    import torch
    from huggingface_hub import hf_hub_download
    from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
    from nemo.collections.asr.models import ASRModel
    from omegaconf import OmegaConf

    training_rows, validation_rows = read_training_rows()
    model = ASRModel.restore_from(hf_hub_download(MODEL_ID, MODEL_FILE))
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.joint.parameters():
        parameter.requires_grad = True
    model.setup_training_data(OmegaConf.create({"manifest_filepath": str(write_manifest("train", training_rows, soundfile)), "sample_rate": 16000, "batch_size": 2, "shuffle": True, "num_workers": 2, "pin_memory": True, "max_duration": 30.0, "min_duration": 0.1, "use_lhotse": False}))
    model.setup_validation_data(OmegaConf.create({"manifest_filepath": str(write_manifest("validation", validation_rows, soundfile)), "sample_rate": 16000, "batch_size": 1, "shuffle": False, "num_workers": 2, "pin_memory": True, "max_duration": 30.0, "min_duration": 0.1, "use_lhotse": False}))
    model.setup_optimization({"name": "adamw", "lr": learning_rate, "weight_decay": 0.01})
    checkpoint = ModelCheckpoint(dirpath="/tmp/checkpoints", monitor="val_wer", mode="min", save_top_k=1)
    trainer = pl.Trainer(accelerator="gpu", devices=1, max_epochs=epochs, precision="16-mixed", logger=False, callbacks=[checkpoint, EarlyStopping(monitor="val_wer", mode="min", patience=3)], enable_model_summary=False, log_every_n_steps=1, num_sanity_val_steps=0)
    started = time.perf_counter()
    trainer.fit(model)
    model.load_state_dict(torch.load(checkpoint.best_model_path, map_location="cpu", weights_only=False)["state_dict"])
    run_dir = output_dir(run_name)
    model.save_to(run_dir / "model.nemo")
    metrics = {"model": MODEL_ID, "adaptation": "joint_only", "completed_epochs": trainer.current_epoch + 1, "learning_rate": learning_rate, "train_clips": len(training_rows), "validation_clips": len(validation_rows), "best_validation_word_error_rate": float(checkpoint.best_model_score), "training_seconds": time.perf_counter() - started}
    save_run(run_dir, metrics)
    return metrics


@app.local_entrypoint()
def main(run_name: str = "parakeet-joint-experiment", epochs: int = 20, learning_rate: float = 1e-5) -> None:
    print(json.dumps(train.remote(run_name=run_name, epochs=epochs, learning_rate=learning_rate), indent=2))
