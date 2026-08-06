# Dysarthria ASR App

Nuxt frontend for the dysarthria ASR prototype.

It provides the accessible speaker-facing UI: recording, mode switching, phrase suggestions, browser TTS, copy/share actions, WhatsApp sharing, and voice commands.

## Setup

```sh
pnpm install
```

## Development

Start the backend first from `../backend`, then run:

```sh
pnpm dev
```

Open <http://localhost:3000>.

The app proxies `/api/*` to `NUXT_API_BASE`, defaulting to `http://127.0.0.1:8000`.

```sh
NUXT_API_BASE=http://127.0.0.1:8000 pnpm dev
```

## Checks

```sh
pnpm typecheck
pnpm test
```

## Production

```sh
pnpm build
pnpm preview
```

## iPhone installation

Serve the app with HTTPS. On the iPhone, open the app in Safari, tap Share,
then tap **Add to Home Screen**. The app opens in standalone mode with the
Sprechen icon.

The service worker updates the app automatically. It caches the current phrase
and category data after use. Audio transcription still needs the backend and an
internet connection.

To regenerate the PWA icons after changing `public/icon.svg`, run:

```sh
pnpm generate-pwa-assets
```
