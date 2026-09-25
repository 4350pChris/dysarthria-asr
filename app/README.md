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

## Checks

```sh
pnpm typecheck
pnpm test
```
