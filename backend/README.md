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

## Checks

```sh
uv run ruff check src tests
uv run pyright
uv run pytest
```
