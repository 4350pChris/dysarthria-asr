# dysarthria-asr

A German speech-assistance prototype for a person with dysarthria. The Nuxt web app records short utterances, gives text suggestions, and can speak, copy, or share the selected text. It saves app recordings and imported WhatsApp voice messages in one local corpus for review and later ASR training.

## Features

- Push-to-talk recording with automatic silence stop
- German `faster-whisper` (`large-v3-turbo` on CPU) for every recording
- Saved phrases, editable categories, and generated German phrase candidates
- Math mode for spoken German arithmetic
- Spoken German emoji names, for example `weißes Herz emoji` → 🤍
- Browser text-to-speech, copy, native share, and WhatsApp-link fallback
- Voice commands for recording, text actions, mode changes, suggestions, and categories
- A PWA that can be installed on an iPhone
- SQLite storage for audio clips, ASR drafts, corrected transcripts, and label state
- Import of individual audio files or WhatsApp chat-export ZIP files
- Guided reading with short German Tatoeba prompts, one reviewed audio clip per prompt
- Training-data ZIP export with reviewed audio and labels

## Project layout

- `app/`: Nuxt frontend and PWA
- `backend/`: FastAPI API, ASR integration, SQLite persistence, and legacy static UI
- `backend/seed/phrases.csv`: default phrase seed used in containers
- `data/phrases.csv`: local phrase seed, when present
- `data/audio/`: saved audio clips; not committed
- `data/app.sqlite`: local SQLite database; not committed

## Run locally

Requirements: Python 3.14+, [uv](https://docs.astral.sh/uv/), Node.js 24+, and pnpm 11.

Start the backend:

```sh
cd backend
uv sync
uv run uvicorn src.app:app --reload
```

The API listens on <http://127.0.0.1:8000>. The first server-side transcription downloads the Whisper model.

## Deploy a tuned ASR model

The backend uses the unchanged `large-v3-turbo` model by default. To deploy a
promoted local CTranslate2 model, set `ASR_MODEL` to its directory when you
start the backend:

```sh
cd backend
ASR_MODEL=/absolute/path/to/deployed-model uv run uvicorn src.app:app --host 127.0.0.1 --port 8000
```

The model directory must be made by
`alignment-tools/promote_whisper_lora.py`. Set a different directory to switch
model versions. Remove `ASR_MODEL` to return to the baseline.

For a private Hugging Face model repository, use its model ID and a read-only
token from the deployment secret store. Pin `ASR_MODEL_REVISION` to a commit
hash. Do not add the token to a source file, image, or repository.

```sh
cd backend
ASR_MODEL=your-org/dysarthria-asr-speaker-v1 \
ASR_MODEL_REVISION=commit-hash \
ASR_HF_TOKEN=read-only-token \
ASR_MODEL_CACHE_DIR=/var/lib/dysarthria-asr/models \
uv run uvicorn src.app:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```sh
cd app
pnpm install
pnpm dev
```

Open <http://localhost:3000>. The frontend sends `/api/*` requests to `NUXT_API_BASE`, which defaults to `http://127.0.0.1:8000`.

To use another backend URL:

```sh
cd app
NUXT_API_BASE=https://example.com pnpm dev
```

## Use the app

1. Start the backend and frontend, then open the Nuxt app.
2. Select a saved phrase or tap `Aufnehmen` and speak.
3. Wait for silence stop. Select a suggestion, or use math mode.
4. Use `Vorlesen`, copy the text, or share it. Native share is tried first; a WhatsApp tab opens only as a fallback. The app never sends a message without user action.
5. Use `Lesetraining aufnehmen` to read one short displayed text at a time. You can listen back, retry, or save each take.
6. Open `/labeling` to review saved recordings and prepare training data.

When the backend starts, it downloads Tatoeba's German sentence export into `data/tatoeba/` only if the local cache does not already exist. The app selects a random set of short prompts from that cache; it does not fetch a prompt while recording. Each saved label records `Tatoeba` as its source.

To manage saved phrases, open `/phrases`. You can add, rename, and delete categories, and add, edit, or delete phrases.

## Voice commands

Start voice control with `Sprachsteuerung starten`.

- Record: `aufnehmen`, `aufnahme`, `start`, `los`
- Stop: `stopp`, `stop`, `anhalten`, `fertig`
- Speak: `vorlesen`, `sagen`, `sprich`, `sprechen`
- Copy: `kopieren`, `kopie`, `abschreiben`
- Share: `teilen`, `senden`, `schicken`, `whatsapp`, `verschicken`
- Modes: `sätze`, `satzmodus`, `sätze modus`, `mathe`, `mathemodus`
- Suggestions: `weiter`, `nächster`, `nächste`, `nein`, `vorheriger`, `vorherige`

On the category page, say a category name, for example `Familie`, or say `Kategorie Familie`.

Browser speech recognition differs by browser. Each saved label records if the browser or the server produced the ASR text.

## Labeling and export

Open `/labeling` to review app recordings, guided-reading clips, and WhatsApp uploads. Filter by source, status, uncertain labels, or missing ASR text. You can correct a transcript, add notes, mark it as `labeled`, `draft`, or `skipped`, and delete one recording. When the missing-ASR filter is active, you can also delete all matching recordings.

Guided-reading clips are saved with the exact displayed prompt, marked `labeled`, and included in the training ZIP immediately. The included texts are original app content rather than scraped web pages, so every saved pair has a known local source.

On `/whatsapp-import`, upload audio files or a WhatsApp export ZIP. For a ZIP, select the speaker whose audio you want to import. Files with no ASR text are skipped.

A recording is training-ready only when it has a non-empty corrected transcript, its status is `labeled`, and it is not marked `unsure`. Download the reviewed set from `/api/labeling/training-data.zip`. The ZIP contains the audio files, `training-labels.csv`, and a short `README.txt`.

The database is kept between restarts. Startup creates missing tables and adds missing seed data without deleting existing recordings or labels.

## Model benchmark

Use the downloaded training-data ZIP to compare local Whisper models. This tool
does not change the app or the backend model.

```sh
cd backend
uv run python scripts/benchmark_asr.py /path/to/dysarthria-asr-training-data.zip \
  --model small \
  --model medium \
  --model large-v3-turbo \
  --output-dir reports/asr-baseline
```

The first use downloads each model. The command writes `summary.csv` with one
row per model, and `details.csv` with one row per recording and model. Both use
case- and punctuation-insensitive German word and character error rates. Use a
local converted CTranslate2 model with `--model label=/path/to/model`.

## API

- `POST /api/transcribe`
- `GET`, `POST /api/phrases`
- `PATCH`, `DELETE /api/phrases/{phrase_id}`
- `GET`, `POST /api/categories`
- `PATCH`, `DELETE /api/categories/{category_id}`
- `GET /api/candidates/generated`
- `GET /api/grammar`
- `PATCH /api/grammar/patterns/{pattern_id}`
- `PATCH /api/grammar/values/{value_id}`
- `POST /api/labeling/import`
- `POST /api/labeling/import/senders`
- `GET /api/labeling/items`
- `PATCH`, `DELETE /api/labeling/items/{audio_id}`
- `DELETE /api/labeling/items/empty-asr`
- `GET /api/labeling/audio/{audio_id}`
- `GET /api/labeling/training-data.zip`

## Model benchmark

Use an exported training-data ZIP, or an extracted copy of it, to compare local Whisper models. This tool does not change the app or its configured ASR model.

```sh
cd backend
uv run python scripts/benchmark_asr.py /path/to/dysarthria-asr-training-data.zip \
  --model small \
  --model medium \
  --model large-v3-turbo \
  --output-dir reports/asr-baseline
```

The first run downloads named models. The command writes `summary.csv` with one row per model and `details.csv` with one row per recording and model. Metrics ignore case and punctuation. Use `--model label=/path/to/model` for a local CTranslate2 model. Run the command with `--help` to see device, compute type, beam size, language, and voice-activity options.

## Checks

Backend:

```sh
cd backend
uv run pytest
```

Frontend:

```sh
cd app
pnpm typecheck
pnpm test
```

## Docker

Build and run the backend:

```sh
cd backend
docker build -t dysarthria-asr-backend .
docker run --rm -p 8000:8000 dysarthria-asr-backend
```

Build and run the frontend:

```sh
cd app
docker build -t dysarthria-asr-app .
docker run --rm -p 3000:3000 -e NUXT_API_BASE=http://host.docker.internal:8000 dysarthria-asr-app
```

For iPhone installation, serve the frontend through HTTPS. Open it in Safari, select Share, then select **Add to Home Screen**. To regenerate PWA icons after you change `app/public/icon.svg`, run `pnpm generate-pwa-assets` in `app/`.
