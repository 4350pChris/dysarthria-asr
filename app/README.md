# Dysarthria ASR frontend

Nuxt frontend and PWA for the Dysarthria ASR project.

See the [main README](../README.md) for the project overview, screenshots, requirements, and backend setup.

## Development

Start the backend first. Then run:

```sh
pnpm install
pnpm dev
```

The app runs at <http://localhost:3000>. It sends API requests to `NUXT_API_BASE`, which defaults to `http://127.0.0.1:8000`.

## Checks

```sh
pnpm typecheck
pnpm test
```
