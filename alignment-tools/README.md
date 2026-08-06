# Reading-audio alignment tools

This is an isolated project. It does not change the app or the backend Python environment.

It uses Qwen's German forced aligner to map supplied text to audio. Use audio parts of five minutes or less. For the 12-minute recording, split the audio and the matching text into three corresponding parts first.

Create the isolated environment:

```sh
cd alignment-tools
uv sync
```

Try the first short part on the MacBook:

```sh
uv run python align_reading.py reading-part-01.wav reading-part-01.txt \
  --output output/part-01-alignment.csv
```

The command uses the Apple GPU through PyTorch MPS when available. Use `--device cpu` if MPS does not work. The first run downloads the model.

The CSV has one aligned unit per row. Review it before clip generation. Do not use it directly as training data.
