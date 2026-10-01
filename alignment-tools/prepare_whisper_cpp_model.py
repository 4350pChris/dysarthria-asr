from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
from peft import PeftModel
from transformers import WhisperForConditionalGeneration, WhisperProcessor


def command_output(command: list[str]) -> str:
    return subprocess.check_output(command, text=True).strip()


def git_revision(path: Path) -> str:
    try:
        return command_output(["git", "-C", str(path), "rev-parse", "HEAD"])
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge a Whisper LoRA adapter and create a quantized whisper.cpp GGML model."
    )
    parser.add_argument("adapter", type=Path, help="Training output directory that contains adapter/.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for the GGML release artifact.")
    parser.add_argument("--whisper-cpp-dir", type=Path, required=True, help="Local whisper.cpp checkout with a built whisper-quantize executable.")
    parser.add_argument("--whisper-source-dir", type=Path, required=True, help="Local openai/whisper checkout used by convert-h5-to-ggml.py.")
    parser.add_argument("--quantization", default="q5_1", choices=("q4_0", "q4_1", "q5_0", "q5_1", "q8_0"))
    arguments = parser.parse_args()

    adapter_dir = arguments.adapter.resolve() / "adapter"
    adapter_config_path = adapter_dir / "adapter_config.json"
    whisper_cpp_dir = arguments.whisper_cpp_dir.resolve()
    whisper_source_dir = arguments.whisper_source_dir.resolve()
    output_dir = arguments.output_dir.resolve()
    converter = whisper_cpp_dir / "models" / "convert-h5-to-ggml.py"
    quantizer = whisper_cpp_dir / "build" / "bin" / "whisper-quantize"

    if not adapter_config_path.is_file():
        raise ValueError(f"Adapter output does not contain adapter/adapter_config.json: {arguments.adapter}")
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    if not converter.is_file():
        raise FileNotFoundError(f"whisper.cpp converter is missing: {converter}")
    if not quantizer.is_file():
        raise FileNotFoundError(f"Build whisper.cpp first; quantizer is missing: {quantizer}")
    if not (whisper_source_dir / "whisper" / "model.py").is_file():
        raise FileNotFoundError(f"OpenAI Whisper source is missing: {whisper_source_dir}")

    adapter_config = json.loads(adapter_config_path.read_text(encoding="utf-8"))
    model_name = adapter_config["base_model_name_or_path"]

    with tempfile.TemporaryDirectory(prefix="dysarthria-asr-whisper-cpp-") as temporary_name:
        temporary_dir = Path(temporary_name)
        merged_dir = temporary_dir / "merged"
        converted_dir = temporary_dir / "converted"
        release_dir = temporary_dir / "release"
        converted_dir.mkdir()
        release_dir.mkdir()

        model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.float32)
        merged_model = PeftModel.from_pretrained(model, adapter_dir).merge_and_unload(safe_merge=True)
        merged_model.save_pretrained(merged_dir, safe_serialization=True)
        WhisperProcessor.from_pretrained(adapter_dir).save_pretrained(merged_dir)

        subprocess.run(
            [sys.executable, str(converter), str(merged_dir), str(whisper_source_dir), str(converted_dir)],
            check=True,
        )
        converted_model = converted_dir / "ggml-model.bin"
        if not converted_model.is_file():
            raise FileNotFoundError(f"whisper.cpp conversion did not create: {converted_model}")

        model_path = release_dir / f"ggml-model-{arguments.quantization}.bin"
        subprocess.run(
            [str(quantizer), str(converted_model), str(model_path), arguments.quantization],
            check=True,
        )

        manifest = {
            "base_model": model_name,
            "adapter_output": str(arguments.adapter.resolve()),
            "format": "ggml",
            "quantization": arguments.quantization,
            "model_file": model_path.name,
            "model_size_bytes": model_path.stat().st_size,
            "sha256": sha256(model_path),
            "whisper_cpp_revision": git_revision(whisper_cpp_dir),
            "whisper_source_revision": git_revision(whisper_source_dir),
        }
        (release_dir / "dysarthria-asr-model.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(release_dir), str(output_dir))

    print(f"Wrote browser model to {output_dir / model_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
