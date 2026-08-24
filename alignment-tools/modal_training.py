from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import modal


PROJECT_DIR = Path(__file__).parent
DATASET_DIR = PROJECT_DIR / "data/datasets/current"
SPLIT_PATH = DATASET_DIR / "split.csv"
REMOTE_DATASET_DIR = Path("/data")
OUTPUT_VOLUME = modal.Volume.from_name("dysarthria-asr-training-results", create_if_missing=True)
REMOTE_SPLIT_PATH = Path("/split.csv")


def training_image(*packages: str, env: dict[str, str] | None = None) -> modal.Image:
    image = (
        modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.10")
        .entrypoint([])
        .uv_pip_install(*packages, extra_index_url="https://download.pytorch.org/whl/cu128", extra_options="--index-strategy unsafe-best-match")
    )
    if env:
        image = image.env(env)
    return image.add_local_file(PROJECT_DIR / "modal_training.py", remote_path="/root/modal_training.py").add_local_dir(DATASET_DIR, remote_path=str(REMOTE_DATASET_DIR)).add_local_file(SPLIT_PATH, remote_path=str(REMOTE_SPLIT_PATH))


def read_split_rows() -> list[dict[str, str]]:
    with REMOTE_SPLIT_PATH.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    return rows


def read_training_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows = read_split_rows()
    train = [row for row in rows if row["split"] == "train"]
    validation = [row for row in rows if row["split"] == "validation"]
    if not train or not validation:
        raise ValueError("Split must contain training and validation clips.")
    return train, validation


def write_manifest(name: str, rows: list[dict[str, str]], soundfile) -> Path:
    path = Path("/tmp") / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            audio_path = REMOTE_DATASET_DIR / row["audio_file"]
            info = soundfile.info(audio_path)
            output.write(json.dumps({"audio_filepath": str(audio_path), "duration": info.frames / info.samplerate, "text": row["transcript"]}, ensure_ascii=False) + "\n")
    return path


def output_dir(run_name: str) -> Path:
    if not run_name or "/" in run_name or "\\" in run_name:
        raise ValueError("run_name must be a single directory name.")
    path = Path("/output") / run_name
    if path.exists():
        raise FileExistsError(f"Output already exists: {path}")
    path.mkdir()
    return path


def save_run(path: Path, metrics: dict[str, object]) -> None:
    (path / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(REMOTE_SPLIT_PATH, path / "split.csv")
    OUTPUT_VOLUME.commit()
