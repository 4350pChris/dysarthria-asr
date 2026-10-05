# Dysarthria ASR backend

FastAPI backend for the Dysarthria ASR project. It transcribes German speech, manages saved phrases and labels, and stores the local audio corpus in SQLite.

See the [main README](../README.md) for the project overview, screenshots, and results.

## Run locally

Requirements: Python 3.14 or later and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
ASR_MODEL=mobiuslabsgmbh/faster-whisper-large-v3-turbo \
  uv run uvicorn src.app:app --reload
```

The API runs at <http://127.0.0.1:8000>. The first transcription downloads the configured model.

`ASR_MODEL` is required. Set it to a Hugging Face model ID, optionally with an `@revision`, or to a local CTranslate2 model directory. For a private model repository, set `HF_TOKEN` in the environment. Do not store the token in this repository.

## Data and services

- `data/app.sqlite` stores phrases, categories, recordings, and labels.
- `data/audio/` stores recorded and imported audio files.
- On startup, the service adds German Tatoeba prompts when no local prompt cache exists.
- The backend accepts requests from the local Nuxt app at port 3000.

Audio and transcripts can be sensitive data. Keep `data/` local unless you have clear permission to share it.

## Live transcription

The app streams 16 kHz PCM over `/api/transcribe/stream`. The server keeps a
rolling window and re-decodes it on every update, so live text is only a
preview; the final authoritative text comes from `/api/transcribe` on the whole
recording. Live decoding uses faster settings than the final pass:

- `ASR_LIVE_MODEL` - a smaller CTranslate2 model for previews; defaults to `ASR_MODEL`.
- `ASR_LIVE_WINDOW_SECONDS` - default `5`.
- `ASR_LIVE_UPDATE_SECONDS` - default `1`.

Live previews always decode with beam size 1; the final pass uses 3.

Model size dominates on CPU. A local 5-second window took about 1.0 s with the
adapted small model and 5.1 s with the adapted large model at beam 1; beam size
changed large-model latency by around 20%. Point `ASR_LIVE_MODEL` at a small
model, or lower `ASR_LIVE_WINDOW_SECONDS`, when live text lags.

## Text review

The recording result can mark possible recognition errors. The user must approve each change.
If the checker is unavailable, the user can edit the text directly.
The original recording and ASR text stay unchanged.
Edited text stays a draft until the full recording is checked for training.

The checker calls OpenRouter with the model in `TEXT_REVIEW_MODEL`
(`qwen/qwen3-235b-a22b-2507` by default). Set `OPENROUTER_API_KEY` in the
environment, as you do for `ASR_MODEL` and `HF_TOKEN`. The request contains the
displayed text, so keep the key on your own server and check the provider policy.
Set `TEXT_REVIEW_URL` only to point at a different OpenAI-compatible endpoint.
The request disallows providers that collect data; that is not a guarantee of
zero retention.

The corpus, prompt variants, and scoring harness live in
`alignment-tools/review-eval/`. Re-run them before changing the prompt or model.
No tested model is safe enough to apply suggestions without review: they are
hints, and roughly one critical case in nine still gets a meaning-changing
suggestion.

To run the checker over saved recordings with checked labels:

```sh
uv run python -m src.transcript_review --limit 30
```

Each output line has the original text, checked text, suggestions, and response time.
Check false warnings, missed errors, and suggestion accuracy.

## Checks

```sh
uv run ruff check src tests
uv run pyright
uv run pytest
```
