# dysarthria-asr

German dysarthria ASR prototype for one speaker.

The app records short utterances, transcribes them with Whisper, suggests likely German phrases, speaks the selected text with browser TTS, and stores every recording in a unified audio corpus for later labeling. The current user-facing app is the Nuxt frontend in `app/`; the FastAPI backend also still serves the older static prototype at `/`.

## Current Features

- Push-to-talk recording with automatic silence stop
- German ASR via `faster-whisper` using the `small` model on CPU
- Phrase suggestions from saved phrases plus generated grammar candidates
- Math mode for spoken German arithmetic
- Browser TTS for the selected recognized text
- Copy and share actions for recognized text
- Native Web Share first, WhatsApp link fallback
- Voice commands for recording, reading, copying, sharing, mode switching, and suggestion navigation
- Persistent SQLite storage for a unified audio corpus and transcription labels
- Dedicated labeling page for reviewing app recordings and WhatsApp uploads
- CSV export for reviewed training labels

## Project Layout

- `backend/`: FastAPI API, ASR integration, SQLite persistence, static prototype
- `app/`: Nuxt frontend used by the deployed app
- `data/phrases.csv`: editable starter phrase list
- `data/audio/`: recorded audio clips, not committed
- `data/app.sqlite`: SQLite database with phrases, grammar rows, audio clips, and labels, not committed

## Backend Setup

```sh
cd backend
uv sync
```

Run the backend:

```sh
cd backend
uv run uvicorn src.app:app --reload
```

The backend listens on <http://127.0.0.1:8000>. The first transcription downloads the `small` Whisper model used by `faster-whisper`.

## Frontend Setup

```sh
cd app
pnpm install
```

Run the Nuxt app:

```sh
cd app
pnpm dev
```

Open <http://localhost:3000>. The frontend proxies `/api/*` to the backend configured by `NUXT_API_BASE`, defaulting to `http://127.0.0.1:8000`.

To point the frontend at a different backend:

```sh
NUXT_API_BASE=https://example.com pnpm dev
```

## Usage

1. Start the backend and frontend.
2. Open the Nuxt app.
3. Tap `Aufnehmen`, speak, and wait for automatic silence stop.
4. Use the top suggestion, choose another suggestion, or switch to math mode.
5. Use `Vorlesen`, `WhatsApp`, or tap the recognized text to copy it.
6. Review saved clips later at `/labeling` before using them for training.

The WhatsApp action uses `navigator.share()` when available. If native sharing is unavailable or fails, it opens a new WhatsApp tab with the recognized text prefilled. The app never silently sends a message.

## Voice Commands

Start voice control with `Sprachsteuerung starten`.

Recognized commands include:

- `aufnehmen`, `aufnahme`, `start`, `los`
- `stopp`, `stop`, `anhalten`, `fertig`
- `vorlesen`, `sagen`, `sprich`, `sprechen`
- `kopieren`, `kopie`, `abschreiben`
- `teilen`, `senden`, `schicken`, `whatsapp`, `verschicken`
- `sätze`, `satzmodus`, `sätze modus`
- `mathe`, `mathemodus`, `mathe modus`
- `weiter`, `nächster`, `nächste`, `nein`
- `zurück`, `vorheriger`, `vorherige`
- `hilfe`, `befehle`

Browser speech recognition support varies. Chrome-compatible browsers are the main target for voice control.

## Data And Persistence

Local runtime data is intentionally not committed:

- `data/audio/`: uploaded or recorded audio clips
- `data/app.sqlite`: categories, phrases, grammar seed rows, audio clips, and transcription labels

The database is no longer dropped on app restart. `init_db()` creates missing tables and seeds missing starter rows without deleting existing labels.

The starter phrase list is committed at `data/phrases.csv`. Edit or replace it with `category,text` rows before structured testing.

## Labeling

Open `/labeling` to import WhatsApp voice messages and review all saved recordings.
Both WhatsApp uploads and clips from `Aufnehmen` use the same corpus tables.
ASR output is only a draft; a clip is training-ready only after it is marked
`labeled` and is not marked `unsure`.

Default export:

- `GET /api/labeling/export.csv`: reviewed, non-unsure labels with transcripts
- `GET /api/labeling/export.csv?all=true`: all labels, including drafts and skipped clips

## API

Main backend endpoints:

- `POST /api/transcribe`
- `POST /api/labeling/import`
- `GET /api/labeling/items`
- `GET /api/labeling/items/next`
- `GET /api/labeling/audio/{audio_id}`
- `PATCH /api/labeling/items/{audio_id}`
- `GET /api/labeling/export.csv`
- `GET /api/phrases`
- `POST /api/phrases`
- `DELETE /api/phrases/{phrase_id}`
- `GET /api/candidates/generated`

## Tests

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
