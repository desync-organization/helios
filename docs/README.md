# Helios

Helios is a Next.js 16 application.

## Run locally

```bash
bun install --frozen-lockfile
bun dev
```

Open http://localhost:3000.

## Verify a production build

```bash
bun run build
```

The project includes server-side API routes. For a Tauri-specific static export that omits those routes, set `TAURI_STATIC_EXPORT=true` when building.
