# Helios

Helios is a local prompt-to-site application built with Next.js 16, FastAPI, and Ollama.

## Run locally

```bash
bun dev
```

That single command:

- installs the locked frontend dependencies when missing;
- creates/synchronizes the Python runtime environment when missing;
- starts Ollama when needed and pulls the configured local model when missing;
- starts Helios only after the model is ready;
- starts Next.js on the first available port from `3000` and prints the exact URL;
- stops the processes it owns when you press `Ctrl+C`.

Prerequisites are Bun, Python 3.12+ (or `uv`), and Ollama. The default model is
`llama3.2:latest`; override it with `HELIOS_OLLAMA_SITE_MODEL`. Set
`HELIOS_OLLAMA_SITE_DIGEST` to enforce an exact reviewed Ollama digest. The standalone command never
starts Hermes, Convex, the Worker, or the compatibility gateway because they are not part of the
direct prompt-to-site path.

For frontend-only development, use `bun run dev:web`. The legacy control-plane integration stack is
still available through `bun run dev:control-plane`.

## Verify a production build

```bash
bun run build
```

The project includes server-side API routes. For a Tauri-specific static export that omits those routes, set `TAURI_STATIC_EXPORT=true` when building.
