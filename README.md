# dysarthria-asr

Basic local prototype for testing German ASR with one dysarthric speaker.

The goal is measurement first:

1. record short German phrases
2. transcribe with an existing German-capable ASR model
3. manually correct the result
4. speak the corrected text with German TTS
5. save audio/transcript/correction pairs for later analysis

## Setup

```sh
cd backend
uv sync
```

## Run

```sh
cd backend
uv run uvicorn src.app:app --reload
```

Open <http://127.0.0.1:8000>.

The first transcription downloads the `small` Whisper model used by
`faster-whisper`.

## Data

Local test data is intentionally not committed:

- `data/audio/`: recorded audio clips
- `data/corrections.jsonl`: correction records

The starter phrase list is committed at `data/phrases.csv`. Edit or replace it
with your own `category,text` rows before structured testing.

Each correction record stores:

- timestamp
- audio id
- audio file
- expected German text
- raw ASR transcript
- corrected German text
- whether the raw ASR was understandable
- optional notes

## First Test Set

Start with 100-200 useful German phrases and record each 3-5 times. Keep the
first run quiet, short, and push-to-talk. Decide whether to continue only after
checking how much of the raw ASR output is recoverable.
