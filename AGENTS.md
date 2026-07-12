# Repository Guidelines

## Product Scope and Ownership

`docs/soul.md` is the product source of truth; the team documents define delivery ownership. Hermes is the agency; Helios is its runtime. The existing Next.js frontend in `src/` and `public/` is accepted as complete and frozen. Do not add pages, presentation components, styles, route trees, a Vite app, or an `apps/dashboard` replacement unless explicitly assigned. Server-only hardening in `src/app/api/` must be coordinated.

Keep work in its owner area: `runtime/` and `agents/` (runtime), `convex/`, `apps/worker/`, `packages/contracts/`, `policy/`, `infra/`, `.github/` (control plane), and `training/`, `datasets/`, `evals/`, `gateway/`, `tests/e2e/`, `evidence/` (model quality and proof). Coordinate contract changes with every consumer before merging.

## Structure and Development Commands

The current app uses App Router routes and API handlers in `src/app/`, shared UI in `src/components/`, state/helpers in `src/lib/`, static assets in `public/`, and build contracts in `docs/`. Use Bun; `bun.lock` is authoritative. Do not introduce pnpm workspace assumptions or regenerate/commit `package-lock.json`.

```bash
bun install --frozen-lockfile  # install locked dependencies
bun dev                        # run the frontend locally
bun run lint                   # run ESLint and Next.js checks
bun run build                  # create a production build
TAURI_STATIC_EXPORT=true bun run build  # Tauri build without API routes
```

Run the relevant runtime, contract, gateway, evaluation, or E2E tests when those owned modules exist. Never represent a planned service, screen, metric, or test as implemented evidence.

## Style and Testing

Use strict TypeScript, `@/*` aliases, four-space indentation, double quotes, semicolons, and trailing commas. Name React components and types in PascalCase, functions/hooks in camelCase, and files in kebab-case (for example, `settings-dialog.tsx`). Keep shadcn primitives in `src/components/ui/` and compose them in feature code.

Before each commit, run `bun run lint` and the affected build/tests. Hard failures in builds, tests, security scans, or contract checks are blockers; they cannot be waived by judgment. Use deterministic fixtures, redact secrets immediately, and rerun affected tests/scans after a remediation.

## Commits and Pull Requests

Commit frequently: make a focused commit whenever a coherent, verified unit is complete. Use imperative Conventional Commit-style subjects, such as `feat: add runtime health endpoint`, `fix: reject expired lease`, or `docs: clarify gateway contract`. Do not add `Co-authored-by` trailers or name Codex as a co-author.

Keep PRs scoped, describe user-visible and contract impacts, link issues, attach UI evidence when applicable, and list commands run. Never force-push consumed checkpoints. Preserve secrets, credentials, private code, and raw security findings from commits, logs, fixtures, screenshots, and event artifacts.
