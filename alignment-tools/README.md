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
uv run mlx-qwen3-asr parts/part-01.ogg --language German --timestamps -f json -o output/mlx
```

Then make a review CSV from the exact source text:

```sh
uv run python align_reading.py part-01.txt output/mlx/part-01.json \
  --output output/part-01-alignment.csv
```

The CSV has short text clips and estimated start and end times. Every row requires review before clip generation. Do not use it directly as training data.

After review, make 16 kHz mono WAV training clips and a manifest that works with the benchmark script:

```sh
uv run python make_training_clips.py \
  --part output/part-01-alignment.csv parts/part-01.ogg \
  --part output/part-02-alignment.csv parts/part-02.ogg \
  --part output/part-03-alignment.csv parts/part-03.ogg \
  --output-dir training-reading
```

Benchmark the current app baseline on the prepared clips:

```sh
uv run python benchmark_asr.py training-reading --model small \
  --output-dir reports/reading-small
```
