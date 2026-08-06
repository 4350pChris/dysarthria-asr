from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


MAX_AUDIO_SECONDS = 300


def audio_duration_seconds(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(audio_path)],
        capture_output=True,
        check=True,
        text=True,
    )
    return float(result.stdout.strip())


def load_aligner(device: str):
    import torch
    from qwen_asr import Qwen3ForcedAligner

    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float16 if device == "mps" else torch.float32
    model = Qwen3ForcedAligner.from_pretrained(
        "Qwen/Qwen3-ForcedAligner-0.6B-hf",
        dtype=dtype,
    )
    return model.to(device), device


def alignment_rows(result) -> list[dict[str, str | float]]:
    units = result[0] if isinstance(result, list) else result
    rows = []
    for unit in units:
        rows.append(
            {
                "text": unit.text,
                "start_seconds": unit.start_time,
                "end_seconds": unit.end_time,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Align one German reading-audio part with its exact text.")
    parser.add_argument("audio", type=Path)
    parser.add_argument("text", type=Path, help="UTF-8 text spoken in this audio part.")
    parser.add_argument("--output", type=Path, required=True, help="CSV output path.")
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    arguments = parser.parse_args()

    duration = audio_duration_seconds(arguments.audio)
    if duration > MAX_AUDIO_SECONDS:
        print("Audio is longer than five minutes. Split it into matching parts first.", file=sys.stderr)
        return 2

    text = arguments.text.read_text(encoding="utf-8").strip()
    if not text:
        print("Text file is empty.", file=sys.stderr)
        return 2

    model, device = load_aligner(arguments.device)
    print(f"Aligning on {device} …", file=sys.stderr)
    result = model.align(audio=str(arguments.audio), text=text, language="German")
    rows = alignment_rows(result)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["text", "start_seconds", "end_seconds"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} aligned units to {arguments.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
