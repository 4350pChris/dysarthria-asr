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

## Local text review

The recording result can mark possible recognition errors. The user must approve each change.
If the checker is unavailable, the user can select a sentence and speak a replacement.
Replacement audio is temporary. The original recording and ASR text stay unchanged.
Edited text stays a draft until the full recording is checked for training.

Start the model service from the project root. Compose runs Ollama and downloads
the model with a separate task. It waits for Ollama to start before the download:

```sh
docker compose up -d ollama-model
docker compose logs -f ollama-model
```

Wait for the task to exit with code 0. It downloads the model, sets its CPU thread
count, and loads it into memory. Press Ctrl+C to stop the log display.
If the download fails, run the start command again and check the logs.
The `ollama-data` volume keeps model files. A later start reuses those files.
`docker compose down` keeps the volume. `docker compose down -v` deletes it.
To stop only the model service, run `docker compose stop ollama`.

The backend uses Ollama's `http://127.0.0.1:11434/api/chat` by default.
The service port accepts connections only from this machine.
Set `TEXT_REVIEW_URL` if the local service has a different address.
Set `TEXT_REVIEW_MODEL` if the service uses a different model name.
To change the model, export `TEXT_REVIEW_MODEL` before you start Compose and the backend.
If the backend runs in the same Compose network, use
`TEXT_REVIEW_URL=http://ollama:11434/api/chat`.
Keep this address on your own server. The request contains the displayed text.
The native API lets the backend set CPU threads. It uses four threads by default.
Export `TEXT_REVIEW_THREADS` before you start Compose and the backend to test a different count.
See [Ollama's local API](https://docs.ollama.com/api/chat).

The Compose service uses the CPU.
Compose keeps the model loaded after a request to avoid repeated load time.
It uses about 3.5 GB of memory for the default model, even when idle.
After a restart, run `docker compose up -d ollama-model` again to load the model
before use. An Ollama health check alone does not mean the model is loaded.
Check speed on the server before use.

On the test Mac (M3 Pro, Docker CPU), eleven threads took 85.7 seconds to produce
32 output tokens. Four threads took 1.1 seconds for the same output.
After the Compose load step, three backend requests took 4.6, 1.8, and 0.7 seconds.
These are short-text checks. They do not measure speed while ASR runs.
The model still proposed a wrong correction for `Brot bewohnen`. Test correction
quality on checked recordings before use.

Before use, test the checker on saved app recordings with checked labels:

```sh
uv run python -m src.transcript_review --limit 30
```

Each output line has the original text, checked text, suggestions, and response time.
Check false warnings, missed errors, and suggestion accuracy. Measure speed while ASR runs too.
The model has not been tested on this user's recordings in this branch.

## Checks

```sh
uv run ruff check src tests
uv run pyright
uv run pytest
```
