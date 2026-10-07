# Dysarthria ASR frontend

Nuxt frontend and PWA for the Dysarthria ASR project.

See the [main README](../README.md) for the project overview, screenshots, requirements, and backend setup.

## Development

Start the backend first. Then run:

```sh
pnpm install
pnpm dev
```

The app runs at <http://localhost:3000>. It sends API and live audio requests to `NUXT_PUBLIC_API_BASE`, which defaults to `http://127.0.0.1:8000`.

For offline speech recognition, set `NUXT_OFFLINE_WHISPER_MODEL_URL` to the Hugging Face model file URL and `NUXT_PUBLIC_OFFLINE_WHISPER_MODEL_VERSION` to a version label. If the model repo is private, set `NUXT_HF_TOKEN` as a server secret. These settings use Nuxt runtime config, so you can change them when the app starts.

## Usage telemetry

Custom events use the existing Umami integration. Configure `NUXT_UMAMI_HOST`
and `NUXT_UMAMI_ID` (see `.env.example`); no separate analytics service is added.

| Event | Properties |
| --- | --- |
| `control_activated` | `control`, `input_method`, `state`, `accepted`, `ignore_reason`, `since_previous_ms` (absent on first activation) |
| `recording_started` | `mode`, `trigger`, `continuing_text`, `auto_stop_enabled`, `start_latency_ms` |
| `recording_start_failed` | `mode`, `trigger`, `error_code` |
| `recording_stopped` | `mode`, `reason`, `duration_ms` |
| `recording_resumed` | `mode`, `previous_stop_reason`, `ready_to_restart_ms` |
| `transcription_completed` | `mode`, `engine`, `outcome`, `stop_to_result_ms` |
| `transcription_failed` | `mode`, `engine`, `error_code`, `elapsed_ms` |
| `text_reset` | `outcome` (`cancelled` / `confirmed`) |
| `review_action` | `action` (`apply` / `keep` / `undo`), `input_method` |

Controls instrumented: `record_toggle`, `review_apply`, `review_keep`, `review_undo`.
Native disabled controls and unmatched voice commands do not produce activation
events. Recording stop reasons are `manual`, `voice_command`, and `silence`;
closing the app mid-recording is not reliably observable. Resume timing runs from
the previous transcription becoming ready to the next accepted start request,
excluding microphone startup latency. Confirmed text reset clears this context.

Use event properties in Umami to inspect ignored/repeated activations, silence-stop
resumes, recording durations, waiting times, failures, resets, and correction undos.
Durations are calculated in the app; no event joins or persistent IDs are required.
These are interaction signals, not spasm detection or confirmed communication
success. Existing copy, share, speak, training, and import events remain unchanged.
No text, audio, command phrases, or raw error messages are sent.

## Checks

```sh
pnpm typecheck
pnpm test
```
