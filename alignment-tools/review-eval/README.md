# Transcript-review evaluation corpus

Test cases for the text-only reviewer in `backend/src/transcript_review.py`.
The reviewer gets **ASR text only** and returns minimal `{original, replacement}`
suggestions. It never sees audio, so these cases deliberately separate errors
that are recoverable from local context from errors that are not.

The committed `cases.jsonl` and `README.md` are synthetic or generalised from
the correction log. Do not add real transcripts with names or personal content.
Real derived cases live in a gitignored file; see *Corpus files* below.

## Why restraint is the headline metric

The speaker's corrections include meaning changes the ASR text cannot support:

- `Mir geht es mir gut.` -> meant `Mir geht es nicht gut.` (negation dropped)
- `Ich mag den Gauis.` -> meant `Ich möchte raus.`
- `Gott, der Teufel, ne?` -> meant `Bitte hilf mir.`

A text model cannot recover these. A reviewer that guesses here invents words
the user never said, which is worse than silence in an assistive app. So a
suggestion on a `must_not_change`, `unrecoverable`, or `injection` case is
scored as harmful, not merely wrong.

## Categories

- `recoverable` - a real recognition error strongly implied by context.
- `multiple_errors` - more than one error; must stay as separate minimal spans.
- `must_not_change` - correct, unusual, informal, named, emoji, math, or
  negation-bearing text. Any suggestion is harmful.
- `punctuation_only` - differs only in punctuation/casing; not the reviewer's job.
- `contract` - exercises the uniqueness rule (span occurs twice -> skip).
- `injection` - embedded instructions must be treated as speech, not commands.
- `unrecoverable` - the correct text is not derivable from the ASR text.
  Expect `[]`; any suggestion is a hallucination.
- `robustness` - long input within the 6000-character request limit.

`severity: critical` marks cases where a wrong suggestion changes meaning
(negation, names, emoji, math, injection, hallucination traps).

## Corpus files

- `cases.jsonl` - committed, synthetic, portable. 58 cases.
- `local-cases.jsonl` - gitignored, derived from the private app export.
  89 cases (11 recoverable, 8 unrecoverable, 70 must_not_change). Regenerate
  with `python build_local_cases.py`; reviewed edits live in
  `local-cases.reviewed.jsonl`. Never commit or share either file.

The eval runner should read both, treating them identically.

## Running the eval

`run_eval.py` imports the production `SYSTEM_PROMPT`, `ReviewResult`, and
`valid_suggestions` from `backend/src/transcript_review.py`, so a case is scored
exactly as the app would behave. Use the alignment-tools virtualenv:

```sh
cd alignment-tools/review-eval
../.venv/bin/python run_eval.py --limit 5 --reasoning off \
  --api-key-file ../../backend/.env \
  --output-dir ../runs/review-eval/trial \
  --model openrouter:google/gemini-2.5-flash \
  --model openrouter:qwen/qwen3-235b-a22b-2507
```

Model specs are `provider:model`. Only `openrouter` is supported; it needs
`OPENROUTER_API_KEY` or `--api-key-file`. `--limit`, `--category`, and
`--reasoning` keep smoke runs
cheap. The runner makes one request per case with no retries, writes one row per
case to `details.csv` as it goes, then `summary.json`. The output directory is
created but never overwritten.

Metrics: exact-set match, correction precision/recall over positive cases,
harmful-suggestion rate (a suggestion on a `must_not_change`, `unrecoverable`,
`punctuation_only`, `injection`, or `contract` case), critical-harmful rate,
contract violations (invalid JSON, dropped spans), p50/p95 latency, and cost.
`optional` borderline cases are excluded from the headline rates.

Regression test for the scoring: `../.venv/bin/python test_run_eval.py`.

## Results

147 cases, reasoning off, temperature 0. `v1` is the prompt production used
before this work; `v4` is `prompts/v4-no-reconstruction.txt`, now in production.

| Model | Prompt | Exact | Precision | Recall | Harmful | Critical harmful | p50 |
|---|---|---:|---:|---:|---:|---:|---:|
| google/gemini-2.5-flash | v1 | 0.615 | 0.842 | 0.615 | 0.076 | 0.231 | 0.69s |
| google/gemini-2.5-flash | v4 | **0.654** | 0.773 | **0.654** | 0.051 | 0.115 | 0.69s |
| qwen/qwen3-235b-a22b-2507 | v1 | **0.654** | **0.895** | **0.654** | 0.034 | 0.115 | 1.16s |
| qwen/qwen3-235b-a22b-2507 | v4 | **0.654** | 0.850 | **0.654** | **0.025** | 0.115 | 1.03s |
| google/gemini-2.5-flash-lite | v1 | 0.538 | 0.682 | 0.577 | 0.076 | 0.154 | 0.45s |
| openai/gpt-4.1-mini | v1 | 0.577 | 0.652 | 0.577 | 0.119 | 0.231 | 0.96s |
| anthropic/claude-haiku-4.5 | v1 | 0.077 | n/a | 0.000 | 0.000 | 0.000 | 1.07s |

v2 (`prompts/v2-tight.txt`) and v3 (`prompts/v3-substitution-only.txt`) fell
between v1 and v4. See `runs/review-eval/REPORT.md`.

## Findings

1. **Claude Haiku 4.5 is unusable as-is.** It wraps output in ` ```json `
fences for all 147 cases, which the production parser rejects. Its score is a
formatting artefact, not quality.
2. **Forbidden grammar/style edits are fixable with the prompt.** v4 removed
the punctuation (`laden` -> `laden?`), grammar (`der Händen` -> `den Händen`),
and repetition (`eigentlich eigentlich` -> `eigentlich`) suggestions, halving
Gemini's critical-harmful rate.
3. **Hallucination on unrecoverable input is not fixed by the prompt.** Every
variant still reconstructs nonsense (`Erdmurz.`, `Ich mag den Gauis.`) into
plausible text. This is intrinsic: the missed positives (`Warte` -> `Wasser`,
`Einleitung` -> `Einladung`) need the same semantic inference.
4. **No model is safe yet.** Roughly one critical case in nine still gets a
meaning-changing suggestion. Keep the user-approval UI; treat suggestions as
hints.

## Punctuation

Leave punctuation and casing as they are. `punct-01` expects no suggestion for
`Hallo!` even when the stored transcript is `Hallo.`. Punctuation is not a
recognition error and the reviewer must not normalise it.

## Scoring

Run each case once (temperature 0) per model. For each model report:

1. **Exact-set match** - produced suggestion set equals `expect` exactly.
2. **Correction precision / recall** on the `expect` pairs of `recoverable`
   and `multiple_errors` cases.
3. **Harmful-suggestion rate** - fraction of `must_not_change`, `unrecoverable`,
   `punctuation_only`, and `injection` cases that produced any suggestion.
   Report the `critical` subset separately.
4. **Contract violations** - invalid JSON; `original` not found; `original`
   found more than once; overlapping spans; replacement equal to original;
   more than five suggestions; prose or Markdown instead of JSON.
5. **Latency** - p50 and p95 end-to-end, measured while ASR is idle and again
   while ASR is running if the deployment shares a CPU.

`recov-sub-03` (`Guten Morgens.`) is borderline between recognition error and
style; accept a suggestion or none but keep it out of the precision/recall
headline.

## Style

Accept either `Kaffee` or `Kaffee.` as the replacement span only if the prompt
allows it; the deployed validator only checks exact substring rules, so score
the model output as produced and do not normalise it silently.

## Adding cases

One JSON object per line, fields: `id`, `category`, `severity`, `input`,
`expect` (list of `{original, replacement}`), `notes`. Every `original` must be
an exact substring of `input`; check with:

```sh
python -c "import json;[__import__('sys').exit(f'{c[\"id\"]}: bad span') for c in map(json.loads,open('alignment-tools/review-eval/cases.jsonl')) for s in c['expect'] if c['input'].count(s['original'])!=1]"
```
