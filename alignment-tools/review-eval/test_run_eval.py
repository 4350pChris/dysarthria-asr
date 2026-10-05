import json

import run_eval


def row(category, expected, produced, severity="normal", valid_json=True, raw_count=None, error="", optional=False):
    return {
        "category": category,
        "severity": severity,
        "optional": optional,
        "error": error,
        "valid_json": valid_json,
        "raw_count": len(produced) if raw_count is None else raw_count,
        "expected_json": json.dumps([list(pair) for pair in expected]),
        "suggestions_json": json.dumps([list(pair) for pair in produced]),
        "latency_seconds": 1.0,
        "cost_usd": 0.0,
    }


def test_summarize_scores_harmful_and_corrections():
    rows = [
        row("recoverable", [("Kaffe", "Kaffee")], [("Kaffe", "Kaffee")]),
        row("recoverable", [("Warte", "Wasser")], [("Warte", "Wasser"), ("Warte", "Waßer")]),
        row("must_not_change", [], [("Hallo", "Hi")], severity="critical"),
        row("must_not_change", [], []),
        row("unrecoverable", [], [("Tschüss", "Chill mal")], severity="critical"),
        row("must_not_change", [], [("Ich", "Ich")], raw_count=2),
        row("recoverable", [("Arz", "Arzt")], [], valid_json=False, raw_count=0),
        row("recoverable", [("x", "y")], [], error="URLError: offline", optional=True),
    ]
    summary = run_eval.summarize(rows, "test:model")
    assert summary["errors"] == 1
    # two recoverable corrections, one wrong extra prediction -> tp=2, fp=1, fn=1
    assert summary["correction_precision"] == 2 / 3
    assert summary["correction_recall"] == 2 / 3
    # four scored harmful cases, three produced a suggestion
    assert (summary["critical_harmful_suggestions"], summary["critical_cases"]) == (2, 2)
    assert summary["harmful_cases"] == 4
    assert summary["harmful_rate"] == 3 / 4
    assert summary["critical_harmful_rate"] == 1.0
    assert summary["contract_violations"]["invalid_json"] == 1
    assert summary["contract_violations"]["dropped_invalid_span"] == 1


def test_parse_raw_is_strict():
    assert run_eval.parse_raw('{"suggestions": [{"original": "a", "replacement": "b"}]}') is not None
    assert run_eval.parse_raw('here you go: {"suggestions": []}') is None
    assert run_eval.parse_raw('{"suggestions": [{"original": "a"}]}') is None


if __name__ == "__main__":
    test_summarize_scores_harmful_and_corrections()
    test_parse_raw_is_strict()
    print("ok")
