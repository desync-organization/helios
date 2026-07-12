# Member 2 — Hermes control plane

This folder is the complete Team Member 2 lane from `docs/TEAM_MEMBER_2_CONTROL_PLANE.md`. It adds no
frontend. It owns the durable contracts, Convex schema and APIs, verified Cloudflare ingress, GitHub App
write-back boundary, policy/consent enforcement, memory and retention, security findings, provider
egress, adapter promotion state, alerts/controls, operational scripts, and CI wiring.

## What is implemented

- `packages/contracts/src/` contains the versioned canonical TypeScript contracts: opaque domain IDs,
  the single three-mode task envelope, all 28 artifact types, trace/model metadata, policies, repository
  consent, security findings, build manifests, write-back intents, adapters, evals, and alerts. Every
  external object is strict and schema-versioned, with bounded fields.
- `convex/` defines all durable entities required by `soul.md`, plus webhook delivery deduplication,
  dead letters, and a cursor event feed. Indexed mutations implement task leases, exact-once ingestion,
  runs/spans/artifacts, repository-isolated memory, findings, egress audits, atomic adapter activation /
  rollback, controls, and write-back reservations.
- `apps/worker/` verifies GitHub HMAC over the raw body, suppresses Hermes loops, normalizes every
  supported event, acknowledges before inference, and exposes bounded runtime/provider/write-back
  routes. Provider fallback is consent-authorized by Convex before payload egress.
- `src/github/` is the only GitHub credential consumer. It mints short-lived installation tokens and
  supports comments, labels, milestones, exact duplicate closure, Git Data API branches/PRs, review
  comments, policy/eval PRs, guarded merges, draft releases, build/security PRs, and SARIF uploads.
- `src/policy/writeback-policy.ts` enforces repository identity, current lease, pause/emergency state,
  dry-run/PR-only/live mode, independent exact-hash critic approval, base SHA, protected paths, size,
  tests/checks/security, separate security remediation consent, secret detection, and hard-never rules.
- `policy/` holds eight versioned, validated policy bundles with stable rule IDs.
- `scripts/` provides policy validation, owned-service startup, repository seeding, health checks, demo
  readiness, and the blocking cross-mode evaluation report gate.

## Trust boundary

```text
GitHub webhook -> Worker (HMAC) -> Convex (canonical task + lease)
                                      ^                 |
                                      | spans/artifacts |
                                Helios runtime ---------+
                                      |
                               credential-free intent
                                      v
Worker -> Convex atomic reservation/policy -> GitHub App -> real URL -> Convex completion
```

The runtime and gateway use only a runtime bearer token. The browser receives no server token. GitHub
App and provider keys exist only in Worker/secret-store configuration. Repository installation IDs are
removed from operator/runtime projections and returned only to the authenticated Worker after an atomic
write-back reservation.

## Local verification

From the repository root:

```bash
bun install --frozen-lockfile
bun run test:contracts
bun run test:integration
bun run --cwd "Member 2" test
bun run --cwd "Member 2" check
bun run --cwd "Member 2" check:policies
bun run build
```

The unit/integration suite covers contract versions and bounds, HMAC verification, bot-loop suppression,
lease contention/expiry, repository isolation, monotonic replay, exact-once write-back, critic/hash
matching, pause/emergency controls, protected paths, security read-only mode, raw-secret rejection,
provider consent, retention, and adapter rollback.

## Running services

1. Copy `.env.example` to an untracked local environment and replace every placeholder.
2. Configure Convex and Worker secrets as described in `infra/README.md`.
3. Run `bun run dev:services`. It starts the owned Convex and Worker services and also starts Member 1's
   runtime / Member 3's gateway when their entry points are present.
4. Run `bun run demo:seed`. This onboards the explicit demo repository in `dry-run` and security
   `read-only` mode; it never invents issues or provider consent.
5. Run `bun run demo:check`, then validate maintain/build/security once in dry-run and PR-only before an
   operator explicitly switches to live.

## Runtime HTTP contract

All runtime routes enforce bearer authentication at the Worker and again between Worker and Convex,
request size limits, JSON errors, rate limits, idempotency/sequence rules, and redacted projections.

```text
POST /runtime/claim
POST /runtime/heartbeat
POST /runtime/run/start
POST /runtime/span
POST /runtime/artifact
POST /runtime/run/finish
POST /runtime/task/escalate
POST /runtime/writeback
POST /runtime/security/findings
GET  /runtime/control
GET  /runtime/config/agents
```

Member 3 consumes the canonical `eventFeed` by `(runId, sequence)` and deduplicates by `eventId`. Stored
events label live/dry-run/fixture/replay provenance and preserve actual cost separately from cloud
equivalent cost. A task cannot finish successfully without a persisted HTTPS result URL.

## Deliberately external acceptance items

Deployment, a real GitHub App installation, live repository URLs, and Member 1/3 integration evidence
require their respective credentials/services and are therefore not fabricated here. The provided
deployment manifests, service checks, seed command, and CI gate fail visibly when those prerequisites
are absent. Fixtures and dry runs are never counted as live completion.
