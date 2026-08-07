from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import WhisperForConditionalGeneration, WhisperProcessor


def convert(merged_dir: Path, output_dir: Path, quantization: str) -> None:
    converter = Path(sys.executable).with_name("ct2-transformers-converter")
    if not converter.is_file():
        converter_name = shutil.which("ct2-transformers-converter")
        converter = Path(converter_name) if converter_name else converter
    if not converter.is_file():
        raise RuntimeError("ct2-transformers-converter is not installed in this environment.")
    subprocess.run(
        [
            converter,
            "--model",
            str(merged_dir),
            "--output_dir",
            str(output_dir),
            "--quantization",
            quantization,
            "--copy_files",
            "tokenizer.json",
            "preprocessor_config.json",
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge a Whisper LoRA adapter and convert it for faster-whisper.")
    parser.add_argument("adapter", type=Path, help="Training output directory that contains adapter/.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New CTranslate2 model directory.")
    parser.add_argument("--quantization", default="int8", choices=["int8", "int8_float32", "float16", "float32"])
    arguments = parser.parse_args()

    adapter_dir = arguments.adapter.resolve() / "adapter"
    config_path = adapter_dir / "adapter_config.json"
    if not config_path.is_file():
        raise ValueError(f"Adapter output does not contain adapter/adapter_config.json: {arguments.adapter}")
    if arguments.output_dir.exists():
        raise FileExistsError(f"Output already exists: {arguments.output_dir}")

    adapter_config = json.loads(config_path.read_text(encoding="utf-8"))
    model_name = adapter_config["base_model_name_or_path"]
    merged_dir = arguments.output_dir.parent / f".{arguments.output_dir.name}-merged"
    if merged_dir.exists():
        raise FileExistsError(f"Temporary merged-model directory already exists: {merged_dir}")

    model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.float32)
    merged_model = PeftModel.from_pretrained(model, adapter_dir).merge_and_unload(safe_merge=True)
    merged_model.save_pretrained(merged_dir, safe_serialization=True)
    WhisperProcessor.from_pretrained(adapter_dir).save_pretrained(merged_dir)
    try:
        convert(merged_dir, arguments.output_dir, arguments.quantization)
    finally:
        shutil.rmtree(merged_dir, ignore_errors=True)

    (arguments.output_dir / "dysarthria-asr-model.json").write_text(
        json.dumps(
            {
                "base_model": model_name,
                "adapter_output": str(arguments.adapter.resolve()),
                "quantization": arguments.quantization,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote deployed model to {arguments.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
