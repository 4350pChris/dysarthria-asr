## Frontend components

- Put each new user flow that has its own state, form, or modal in a named component. Keep pages for layout, routing, and wiring only. Do this before adding more than a simple prop or event handler to a page.

## Modal Whisper training

- Do not start Whisper training through `modal run --detach modal_train_whisper_lora.py`. The local entrypoint can disconnect and cancel the remote job before it finishes.
- Start the remote function directly in detached mode instead: `modal run --detach modal_train_whisper_lora.py::train ...`.
- Give every retry a new `--run-name`. After training, check the Modal app logs before downloading the adapter.

## Whisper evaluation

- Before promoting a new Whisper model, benchmark beam sizes 1, 3, and 5 on the fixed held-out test split with the selected VAD settings. The best beam size can change after more training data or different training settings.
- For the current v7 model with tolerant VAD, use `beam_size=1`. It matched beam 3 and 5 on WER and had the best CER.
