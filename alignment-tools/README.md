# Reading-audio alignment tools

This is an isolated project. It does not change the app or the backend Python environment.

It uses MLX Qwen ASR on Apple Silicon to make word timestamps. Then it maps your exact text to these timestamps. Use audio parts of five minutes or less. For the 12-minute recording, split the audio and the matching text into three corresponding parts first.

Create the isolated environment:

```sh
cd alignment-tools
uv sync
```

First, make timestamp JSON with the local Apple GPU:

```sh
uv run mlx-qwen3-asr data/reading/parts/part-01.ogg --language German --timestamps -f json -o runs/alignment/mlx
```

Create editable spoken-text files. They expand the known differences between
the printed text and the speech, such as `Dr. B.` and `vgl. S.`:

```sh
uv run python make_spoken_text.py \
  data/reading/transcripts/part-01.txt \
  data/reading/transcripts/part-02.txt \
  data/reading/transcripts/part-03.txt
```

Review `data/reading/spoken/part-*.txt` and correct every remaining spoken-text difference.
Then make a review CSV from the spoken text:

```sh
uv run python align_reading.py data/reading/spoken/part-01.txt runs/alignment/mlx/part-01.json \
  --output runs/alignment/part-01-alignment.csv
```

The CSV has short text clips and estimated start and end times. Every row requires review. Set `approved` to `yes` only after the audio and text match. The clip tool ignores all unapproved rows and refuses clips outside 2–25 seconds.

After review, make 16 kHz mono WAV training clips and a manifest that works with the benchmark script:

```sh
uv run python make_training_clips.py \
  --part runs/alignment/review-v2/part-01-alignment.csv data/reading/parts/part-01.ogg \
  --part runs/alignment/review-v2/part-02-alignment.csv data/reading/parts/part-02.ogg \
  --part runs/alignment/review-v2/part-03-alignment.csv data/reading/parts/part-03.ogg \
  --output-dir data/datasets/reading-v2
```

Benchmark the current app baseline on the reviewed reading clips:

```sh
uv run python benchmark_asr.py data/datasets/reading-v2 --model small \
  --output-dir runs/reports/reading-v2-small
```

## Deploy a trained adapter

Merge a reviewed LoRA adapter and convert it for the backend's
`faster-whisper` runtime:

```sh
uv run python promote_whisper_lora.py \
  runs/training/whisper-large-v3-turbo-lora-combined-v2 \
  --output-dir models/deployed/whisper-large-v3-turbo-combined-v2-int8
```

Set `ASR_MODEL` to this deployed directory when you start the backend. The
backend requires this setting. Use
`mobiuslabsgmbh/faster-whisper-large-v3-turbo` for the unchanged baseline.

Train the current v2 dataset with turbo:

```sh
uv run python train_whisper_lora.py data/datasets/combined-v2 \
  --model-name openai/whisper-large-v3-turbo \
  --output-dir runs/training/whisper-large-v3-turbo-lora-combined-v2
```

The default settings use 12 epochs, a learning rate of `5e-5`, 10% warmup,
gradient checkpointing, and the checkpoint with the best evaluation loss.
Do not use `--skip-trainer-evaluation` for a normal training run.

Compare the unchanged turbo model and the deployed v2 model on the same held-out split:

```sh
uv run python benchmark_asr.py data/datasets/combined-v2 \
  --split runs/training/whisper-large-v3-turbo-lora-combined-v2/split.csv \
  --model turbo=mobiuslabsgmbh/faster-whisper-large-v3-turbo \
  --model v2=models/deployed/whisper-large-v3-turbo-combined-v2-int8 \
  --output-dir runs/reports/combined-v2-final-comparison
```
