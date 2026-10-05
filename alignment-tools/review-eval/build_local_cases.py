"""Build the private transcript-review corpus from the app export.

The export and its transcripts are private: the generated file stays in this
gitignored directory. It merges the hand-reviewed cases (recoverable errors and
unrecoverable traps) with every unique utterance where ASR and the corrected
transcript agree, which become must_not_change cases.

Usage:
    python build_local_cases.py
    python build_local_cases.py --export ../../data/dysarthria-asr-training-data.zip
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_EXPORT = HERE.parents[1] / "data" / "dysarthria-asr-training-data.zip"
REVIEWED = HERE / "local-cases.reviewed.jsonl"
OUTPUT = HERE / "local-cases.jsonl"


def words(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", unicodedata.normalize("NFKC", text).casefold()))


def read_export(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith("training-labels.csv")]
        if not names:
            raise ValueError(f"No training-labels.csv in {path}")
        text = archive.read(names[0]).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def unique_correct(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        transcript = row.get("transcript", "").strip()
        key = words(transcript)
        if not key or key in seen or words(row.get("asr_text", "")) != key:
            continue
        seen.add(key)
        cases.append({
            "id": f"real-keep-{len(cases):03d}",
            "category": "must_not_change",
            "severity": "normal",
            "input": transcript,
            "expect": [],
            "notes": "Real pair: ASR already matched the corrected transcript.",
        })
    return cases


def read_reviewed() -> list[dict[str, object]]:
    if not REVIEWED.is_file():
        return []
    return [json.loads(line) for line in REVIEWED.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(cases: list[dict[str, object]]) -> None:
    ids: set[str] = set()
    for case in cases:
        if case["id"] in ids:
            raise ValueError(f"Duplicate case id: {case['id']}")
        ids.add(case["id"])
        if not case["input"].strip():
            raise ValueError(f"Empty input in {case['id']}")
        for suggestion in case["expect"]:  # type: ignore[union-attr]
            original = suggestion["original"]
            if case["input"].count(original) != 1:  # type: ignore[operator]
                raise ValueError(f"{case['id']}: {original!r} is not a unique substring")
            if original == suggestion["replacement"]:
                raise ValueError(f"{case['id']}: no-op replacement")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    args = parser.parse_args()
    reviewed = read_reviewed()
    negatives = unique_correct(read_export(args.export))
    cases = reviewed + negatives
    validate(cases)
    OUTPUT.write_text("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {OUTPUT} ({len(reviewed)} reviewed, {len(negatives)} must_not_change)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
