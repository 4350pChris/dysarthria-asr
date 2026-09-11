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

Use the dataset test split to compare models. Do not use it during training or
model selection.

```sh
uv run python benchmark_asr.py data/datasets/current \
  --split data/datasets/current/split.csv \
  --model base=mobiuslabsgmbh/faster-whisper-large-v3-turbo \
  --model adapted=models/deployed/model-name \
  --output-dir runs/reports/model-name
```

The report contains WER, character error rate, and one row per audio clip. Do not compare results from different test splits.

For speakers with long pauses, compare VAD modes on the same test split:

```sh
uv run python benchmark_asr.py data/datasets/current \
  --split data/datasets/current/split.csv \
  --model adapted=models/deployed/model-name \
  --vad-mode default \
  --vad-mode off \
  --vad-mode tolerant \
  --output-dir runs/reports/model-name-vad
```

`tolerant` keeps longer pauses and more audio around speech. Select a VAD mode
from this report before changing the backend setting.

Compare whether Whisper should use earlier text as context inside long clips:

```sh
uv run python benchmark_asr.py data/datasets/current \
  --split data/datasets/current/split.csv \
  --model adapted=models/deployed/model-name \
  --vad-mode tolerant \
  --beam-size 1 \
  --condition-on-previous-text true \
  --condition-on-previous-text false \
  --output-dir runs/reports/model-name-previous-text
```

Use this comparison before changing `condition_on_previous_text` in the
backend. Its best value can change with the model and training data.

## Train and deploy Whisper on Modal

Build `data/datasets/current`. The command downloads the reviewed app export
from `https://asr.ennen.dev/api/labeling/training-data.zip` and combines it
with the reading clips:

```sh
uv run python prepare_combined_training_data.py \
  --replace
```

The builder assigns every normalized transcript to a stable 80% training, 10%
validation, or 10% test group. New recordings of the same text always use the
same group. The validation group selects the checkpoint; the test group is for
the final benchmark only.

Start training with a new run name:

```
uv run modal run modal_train_whisper_lora.py \
  --run-name whisper-large-v3-turbo-lora-experiment-01

mkdir -p runs/training/whisper-large-v3-turbo-lora-experiment-01/adapter
for name in vocab.json tokenizer_config.json tokenizer.json special_tokens_map.json preprocessor_config.json normalizer.json merges.txt generation_config.json added_tokens.json adapter_model.safetensors adapter_config.json; do
  uv run modal volume get dysarthria-asr-training-results \
    /whisper-large-v3-turbo-lora-experiment-01/adapter/$name \
    runs/training/whisper-large-v3-turbo-lora-experiment-01/adapter/$name
done

uv run python promote_whisper_lora.py \
  runs/training/whisper-large-v3-turbo-lora-experiment-01 \
  --output-dir models/deployed/whisper-large-v3-turbo-lora-experiment-01
```

The job uploads private source data to Modal, uses one L4 GPU, and has a
two-hour limit. Do not reuse a run name.

Set `ASR_MODEL` to the deployed model directory when you run the backend. Use the unchanged base model as the benchmark control.

## Prepare a browser model

After a Whisper LoRA run passes its held-out benchmark, merge it and produce a
quantized GGML model for `whisper.cpp` WASM. Build local checkouts of
`ggml-org/whisper.cpp` and `openai/whisper` first. The browser build uses GGML
model files, not GGUF.

```sh
uv run python prepare_whisper_cpp_model.py \
  runs/training/whisper-small-lora-current-v1 \
  --output-dir models/browser/whisper-small-lora-current-v1-q5_1 \
  --whisper-cpp-dir /path/to/whisper.cpp \
  --whisper-source-dir /path/to/whisper \
  --quantization q5_1
```

The command writes one quantized `.bin` model and a manifest with its SHA-256,
size, source revisions, and adapter origin. Benchmark this exact model on the
target iPhone before publishing it.

## Train Parakeet on Modal

The Parakeet joint-only and encoder-LoRA experiments use the same current
dataset and train/validation/test split. They use validation to select the
checkpoint and leave test clips for a later benchmark.

```sh
uv run modal run modal_train_parakeet.py \
  --run-name parakeet-joint-experiment-01

uv run modal run modal_train_parakeet_adapter.py \
  --run-name parakeet-encoder-lora-experiment-01
```
