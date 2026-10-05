## Frontend components

- Put each new user flow that has its own state, form, or modal in a named component. Keep pages for layout, routing, and wiring only. Do this before adding more than a simple prop or event handler to a page.

## Modal Whisper training

- Do not start Whisper training through `modal run --detach modal_train_whisper_lora.py`. The local entrypoint can disconnect and cancel the remote job before it finishes.
- Start the remote function directly in detached mode instead: `modal run --detach modal_train_whisper_lora.py::train ...`.
- Give every retry a new `--run-name`. After training, check the Modal app logs before downloading the adapter.

## Whisper evaluation

- Before promoting a new Whisper model, benchmark beam sizes 1, 3, and 5 on the fixed held-out test split with the selected VAD settings. The best beam size can change after more training data or different training settings.
- For the current v7 model with tolerant VAD, use `beam_size=1`. It matched beam 3 and 5 on WER and had the best CER.
- Live transcription re-decodes a rolling window every update, so it cannot keep up when one window costs more than the update interval. Keep a small model on `ASR_LIVE_MODEL` for the preview and the large model for the final pass, and measure per-window latency before changing the live settings. Publish the live model to the private `dysarthria-asr/amsel-small-ct2` repo; the download and promote steps are in `alignment-tools/README.md`.

## Transcript review

- Before changing the review prompt or model in `backend/src/transcript_review.py`, re-run `alignment-tools/review-eval/run_eval.py` on the 147-case corpus. Restraint matters more than recall: score the harmful and critical-harmful rates alongside exact match.
- Keep the prompt files in `alignment-tools/review-eval/prompts/`. The production prompt is currently `v4-no-reconstruction`.
- Text review calls OpenRouter with `qwen/qwen3-235b-a22b-2507`. Keep `OPENROUTER_API_KEY` in the server environment, never in Git.
- Never commit `local-cases.jsonl` or `local-cases.reviewed.jsonl`. They contain private transcripts; both are gitignored.
