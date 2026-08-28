## Frontend components

- Put each new user flow that has its own state, form, or modal in a named component. Keep pages for layout, routing, and wiring only. Do this before adding more than a simple prop or event handler to a page.

## Modal Whisper training

- Do not start Whisper training through `modal run --detach modal_train_whisper_lora.py`. The local entrypoint can disconnect and cancel the remote job before it finishes.
- Start the remote function directly in detached mode instead: `modal run --detach modal_train_whisper_lora.py::train ...`.
- Give every retry a new `--run-name`. After training, check the Modal app logs before downloading the adapter.
