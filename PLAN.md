# Dysarthria ASR Prototype Plan

## Goal

Build a local measurement prototype for one German speaker with severe
dysarthria.

The first question is not "can we train a model?" The first question is:

> Can existing German ASR recover enough of the speaker's audio that a simple
> correction layer can make the output useful?

Target flow:

```text
record audio -> German ASR -> select phrase -> German TTS -> save speech attempt
```

## Current Prototype

The repo currently contains a small FastAPI + browser prototype:

- `static/index.html`: record/correct/speak UI
- `static/app.js`: browser `MediaRecorder`, API calls, German browser TTS
- `src/app.py`: FastAPI app setup and router registration
- `src/asr.py`: `faster-whisper` German transcription wrapper
- `data/audio/`: local recorded clips, ignored by git
- `data/app.sqlite`: phrases, audio sample metadata, and speech attempts

Run it with:

```sh
cd /Users/chris/Repos/dysarthria-asr
source .venv/bin/activate
uvicorn src.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The first transcription downloads the Whisper `small` model.

## Prototype Scope

Do first:

- German only
- quiet room
- push-to-talk recording
- short phrases
- in-person use
- text output plus German TTS playback
- save every audio/transcript/speech-attempt pair

Do not do yet:

- real-time streaming
- phone-call integration
- voice cloning
- fine-tuning
- cloud accounts/auth
- mobile app packaging
- emergency/medical dependency

## First Test Set

Create 100-200 useful German phrases and record each 3-5 times.

Suggested categories:

- greetings
- requests: water, food, rest, help
- clarification: repeat, slower, yes/no
- personal names
- locations
- medical/care phrases
- common social phrases
- free-form daily phrases

Each saved example should preserve:

```text
audio_file
expected_text
raw_asr_text
corrected_text
was_understandable
notes
```

The current app saves:

```text
created_at
audio_id
raw_transcript
corrected_text
notes
```

Add `expected_text` and `was_understandable` once structured testing starts.

## Evaluation

Measure before improving.

Useful rough metrics:

- exact match rate
- close-enough-to-correct rate
- total failure rate
- common substitutions
- common deleted words
- phrase categories that work or fail

Decision rule:

- If raw ASR is mostly unrecoverable, try AAC or constrained phrase boards.
- If ASR gets structure partly right, add personalized correction.
- If correction still cannot recover enough, only then consider fine-tuning.

## Next Development Steps

1. Add a phrase list screen or importable CSV.
2. Add `expected_text` and `was_understandable` to saved records.
3. Add a speech-attempt review page showing recent attempts.
4. Add fuzzy matching against known phrases.
5. Add simple personal vocabulary/substitution rules.
6. Export results as CSV for analysis.

## Correction Layer Idea

Start simple:

```text
"isch brauch wascha" -> "Ich brauche Wasser."
"ka fe" -> "Kaffee"
"bitte wider holn" -> "Bitte wiederholen."
```

Likely first implementation:

- normalize text
- compare ASR output against known phrase list
- rank suggestions by fuzzy similarity
- let user choose/edit
- save final correction

Avoid custom ML until the baseline data proves it is worth the cost.

## Later Fine-Tuning

Fine-tuning may be useful, but only after collecting enough labeled examples.

Minimum before exploring it:

- several hundred labeled clips
- stable recording setup
- clear baseline ASR metrics
- recurring errors that phrase matching cannot handle
- explicit consent/privacy rules

Possible later candidates:

- Whisper/faster-whisper based workflow
- wav2vec-style speaker adaptation
- constrained intent/phrase classifier for common needs

## Privacy Notes

Audio samples are sensitive biometric/health-adjacent data.

Keep prototype data local by default. Do not upload recordings to cloud services
without explicit informed consent. Treat raw audio as more sensitive than the
corrected text.
