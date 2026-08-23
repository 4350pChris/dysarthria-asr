# Alignment and training tools

These are internal tools for making a reviewed speech dataset and evaluating or training ASR models. They are not needed to run the app.

The workflow can process private speech data. Keep source audio, transcripts, generated datasets, and trained models out of Git unless you have clear permission to publish them.

## Set up

```sh
cd alignment-tools
uv sync
```

## Create a reviewed dataset

Prepare an audio file and its matching text. Split long recordings into matching audio and text parts of five minutes or less.

1. Create word timestamps. This command uses MLX on Apple Silicon:

   ```sh
   uv run mlx-qwen3-asr data/source/session-01.ogg \
     --language German --timestamps -f json -o runs/alignment/timestamps
   ```

2. Create an editable copy of the text. Edit this copy until it matches exactly what the speaker said, including expanded abbreviations and spoken punctuation:

   ```sh
   uv run python make_spoken_text.py data/source/session-01.txt \
     --output-dir runs/alignment/spoken
   ```

3. Map the reviewed text to the timestamp JSON:

   ```sh
   uv run python align_reading.py \
     runs/alignment/spoken/session-01.txt \
     runs/alignment/timestamps/session-01.json \
     --output runs/alignment/review/session-01.csv
   ```

4. Review the CSV. Set `approved` to `yes` only when the audio and text match. The clip tool ignores unapproved rows and rejects clips outside 2–25 seconds.

5. Create 16 kHz mono WAV clips and `training-labels.csv`. Repeat `--part` for each audio part:

   ```sh
   uv run python make_training_clips.py \
     --part runs/alignment/review/session-01.csv data/source/session-01.ogg \
     --output-dir data/datasets/session-01
   ```

## Evaluate models

Use one fixed held-out split to compare models. For example:

```sh
uv run python benchmark_asr.py data/datasets/session-01 \
  --split runs/training/model-name/split.csv \
  --model base=mobiuslabsgmbh/faster-whisper-large-v3-turbo \
  --model adapted=models/deployed/model-name \
  --output-dir runs/reports/model-name
```

The report contains WER, character error rate, and one row per audio clip. Do not compare results from different test splits.

## Train and deploy Whisper

Train a LoRA adapter, then merge and convert it for the backend's `faster-whisper` runtime:

```sh
uv run python train_whisper_lora.py data/datasets/session-01 \
  --output-dir runs/training/model-name

uv run python promote_whisper_lora.py runs/training/model-name \
  --output-dir models/deployed/model-name
```

### Train Whisper on Modal

The Modal job uses the current `combined-v3` dataset and its existing fixed
training/evaluation split. It uploads those private files to Modal as part of
the job image. Do this only if that data handling is acceptable.

```sh
uv run modal run modal_train_whisper_lora.py \
  --run-name whisper-large-v3-turbo-lora-combined-v3-experiment-01

mkdir -p runs/training/whisper-large-v3-turbo-lora-combined-v3-experiment-01/adapter
for name in vocab.json tokenizer_config.json tokenizer.json special_tokens_map.json preprocessor_config.json normalizer.json merges.txt generation_config.json added_tokens.json adapter_model.safetensors adapter_config.json; do
  uv run modal volume get dysarthria-asr-training-results \
    /whisper-large-v3-turbo-lora-combined-v3-experiment-01/adapter/$name \
    runs/training/whisper-large-v3-turbo-lora-combined-v3-experiment-01/adapter/$name
done

uv run python promote_whisper_lora.py \
  runs/training/whisper-large-v3-turbo-lora-combined-v3-experiment-01 \
  --output-dir models/deployed/whisper-large-v3-turbo-lora-combined-v3-experiment-01
```

The job uses one L4 GPU and has a two-hour limit. Its default values match the
local Whisper training script. Do not use the same `--run-name` twice unless
you first remove or rename the old output in the Modal Volume.

Set `ASR_MODEL` to the deployed model directory when you run the backend. Use the unchanged base model as the benchmark control.

## Other experiments

`benchmark_parakeet.py` evaluates a Parakeet model on the same dataset and split. `modal_train_parakeet.py` and `modal_train_parakeet_adapter.py` run Parakeet training jobs on Modal. Use `--help` on each command before a new experiment.
