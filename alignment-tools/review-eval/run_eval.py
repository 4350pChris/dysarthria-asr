"""Score text-review models on the transcript-review corpus.

Reads cases.jsonl and (if present) local-cases.jsonl. Uses the production
system prompt and validation from backend/src/transcript_review.py, so a case
is scored exactly as the app would behave.

Smoke run (cheap, 3 cases per model, no overwrite):
    python run_eval.py --limit 3 --output-dir runs/trial-01 \
      --model openrouter:google/gemini-2.5-flash

Compare models:
    python run_eval.py --output-dir runs/report-01 \
      --model openrouter:google/gemini-2.5-flash \
      --model openrouter:openai/gpt-4.1-mini
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backend" / "src"))

from transcript_review import SYSTEM_PROMPT, ReviewResult, valid_suggestions  # noqa: E402

HARMFUL_CATEGORIES = {"must_not_change", "unrecoverable", "punctuation_only", "injection", "contract"}
CASE_FILES = [HERE / "cases.jsonl", HERE / "local-cases.jsonl"]
DETAIL_FIELDS = [
    "model", "case_id", "category", "severity", "optional", "error", "valid_json", "raw_count",
    "expected_json", "suggestions_json", "raw_response", "latency_seconds", "cost_usd",
]


def load_cases(paths: list[Path]) -> list[dict]:
    cases: list[dict] = []
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(json.loads(line))
    return cases


def parse_raw(raw: str) -> ReviewResult | None:
    try:
        return ReviewResult.model_validate_json(raw)
    except Exception:
        return None


def call_openrouter(model: str, text: str, key: str, reasoning: str, timeout: float, system: str) -> tuple[str, dict]:
    payload: dict = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
        "temperature": 0,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
        "provider": {"data_collection": "deny"},
        "stream": False,
    }
    if reasoning == "off":
        payload["reasoning"] = {"enabled": False}
    elif reasoning != "default":
        payload["reasoning"] = {"effort": reasoning}
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        body = json.load(response)
    return body["choices"][0]["message"]["content"], body.get("usage", {})


def call_model(spec: str, text: str, args: argparse.Namespace) -> tuple[str, dict]:
    provider, _, model = spec.partition(":")
    if not model:
        provider, model = "openrouter", spec
    if provider != "openrouter":
        raise ValueError(f"Unknown provider {provider!r}")
    if not args.api_key:
        raise ValueError("Set OPENROUTER_API_KEY or pass --api-key-file")
    return call_openrouter(model, text, args.api_key, args.reasoning, args.timeout, args.system_prompt)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def summarize(rows: list[dict], model: str) -> dict:
    scored = [row for row in rows if not row["error"]]
    errors = [row for row in rows if row["error"]]
    latencies = [row["latency_seconds"] for row in scored]
    tp = fp = fn = 0
    exact = exact_total = 0
    harmful = harmful_total = 0
    critical_harmful = critical_total = 0
    violations: dict[str, int] = {}
    for row in scored:
        produced = {tuple(pair) for pair in json.loads(row["suggestions_json"])}
        expected = {tuple(pair) for pair in json.loads(row["expected_json"])}
        if not row["valid_json"]:
            violations["invalid_json"] = violations.get("invalid_json", 0) + 1
        if row["raw_count"] != len(produced):
            violations["dropped_invalid_span"] = violations.get("dropped_invalid_span", 0) + 1
        if row["optional"]:
            continue
        if row["category"] in HARMFUL_CATEGORIES:
            harmful_total += 1
            harmful += bool(produced)
            if row["severity"] == "critical":
                critical_total += 1
                critical_harmful += bool(produced)
        else:
            exact_total += 1
            exact += produced == expected
            tp += len(produced & expected)
            fp += len(produced - expected)
            fn += len(expected - produced)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    cost = [row["cost_usd"] for row in scored if row["cost_usd"] is not None]
    return {
        "model": model,
        "cases": len(rows),
        "errors": len(errors),
        "exact_match": exact / exact_total if exact_total else None,
        "exact_match_cases": exact_total,
        "correction_precision": precision,
        "correction_recall": recall,
        "harmful_suggestions": harmful,
        "harmful_cases": harmful_total,
        "harmful_rate": harmful / harmful_total if harmful_total else None,
        "critical_harmful_suggestions": critical_harmful,
        "critical_cases": critical_total,
        "critical_harmful_rate": critical_harmful / critical_total if critical_total else None,
        "contract_violations": violations,
        "latency_p50_seconds": percentile(latencies, 0.5),
        "latency_p95_seconds": percentile(latencies, 0.95),
        "cost_usd": sum(cost) if cost else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", action="append", required=True, help="provider:model, e.g. openrouter:google/gemini-2.5-flash")
    parser.add_argument("--cases", action="append", type=Path, help="Case files; repeat. Defaults to cases.jsonl + local-cases.jsonl.")
    parser.add_argument("--limit", type=int, help="Only the first N cases, for smoke runs.")
    parser.add_argument("--category", action="append", help="Only these categories; repeat.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reasoning", choices=["default", "off", "low", "medium", "high"], default="default")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--api-key-file", type=Path, help="Read the OpenRouter key from this file or .env-style file.")
    parser.add_argument("--system-prompt-file", type=Path, help="Override the system prompt (default: production prompt).")
    args = parser.parse_args()
    args.system_prompt = (
        args.system_prompt_file.read_text(encoding="utf-8")
        if args.system_prompt_file
        else SYSTEM_PROMPT
    )
    args.api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not args.api_key and args.api_key_file:
        for line in args.api_key_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                args.api_key = line.partition("=")[2].strip().strip('"').strip("'")
    if not args.api_key:
        parser.error("Set OPENROUTER_API_KEY or pass --api-key-file.")
    cases = load_cases(args.cases or CASE_FILES)
    if args.category:
        cases = [case for case in cases if case["category"] in set(args.category)]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        parser.error("No cases selected.")
    if not args.output_dir.exists():
        args.output_dir.mkdir(parents=True)
    print(f"{len(cases)} cases x {len(args.model)} models = {len(cases) * len(args.model)} requests", file=sys.stderr)
    summaries = []
    with (args.output_dir / "details.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETAIL_FIELDS)
        writer.writeheader()
        for spec in args.model:
            rows = []
            for index, case in enumerate(cases, 1):
                started = time.perf_counter()
                error = ""
                raw_response = ""
                cost = None
                try:
                    raw_response, usage = call_model(spec, case["input"], args)
                    cost = usage.get("cost")
                except (HTTPError, URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                    error = f"{type(exc).__name__}: {exc}"
                latency = time.perf_counter() - started
                parsed = parse_raw(raw_response) if raw_response else None
                suggestions = valid_suggestions(case["input"], parsed.suggestions) if parsed else []
                rows.append({
                    "model": spec,
                    "case_id": case["id"],
                    "category": case["category"],
                    "severity": case["severity"],
                    "optional": bool(case.get("optional")) or error != "",
                    "error": error,
                    "valid_json": bool(parsed),
                    "raw_count": len(parsed.suggestions) if parsed else 0,
                    "expected_json": json.dumps([[s["original"], s["replacement"]] for s in case["expect"]], ensure_ascii=False),
                    "suggestions_json": json.dumps([[s.original, s.replacement] for s in suggestions], ensure_ascii=False),
                    "raw_response": raw_response,
                    "latency_seconds": round(latency, 3),
                    "cost_usd": cost,
                })
                writer.writerow(rows[-1])
                handle.flush()
                if index % 10 == 0 or index == len(cases):
                    print(f"  {spec}: {index}/{len(cases)}", file=sys.stderr)
            summaries.append(summarize(rows, spec))
    (args.output_dir / "summary.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    keys = ["model", "errors", "exact_match", "correction_precision", "correction_recall",
            "harmful_rate", "critical_harmful_rate", "latency_p50_seconds", "latency_p95_seconds", "cost_usd"]
    print()
    print(" | ".join(key.replace("_seconds", "").replace("correction_", "") for key in keys))
    for summary in summaries:
        print(" | ".join(
            f"{summary[key]:.3f}" if isinstance(summary[key], float) else str(summary[key]) for key in keys
        ))
    print(f"\nDetails and summary in {args.output_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
