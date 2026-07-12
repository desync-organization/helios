# Team Member 2 — Convex Control Plane, Cloudflare, GitHub, and Integrations

## Mission

You own the cloud/control plane and are the repository integration lead. Your job is to make every
Hermes action durable, secure, idempotent, live-queryable, and visible on a real GitHub repository.
Member 1 supplies plans, spans, artifacts, and write-back intents. You persist them, enforce leases
and policies, execute credentialed GitHub actions, feed memory and evals back into later runs, and
expose stable queries to Member 3. You also own the root commands that make the merged project start
and test as one system.

Your code must work with a simulated runtime so you never wait for Member 1. Build a deterministic
`demoRuntime` Convex action or seed script that creates tasks, runs, spans, artifacts, agent events,
eval results, model events, and alerts. Member 3 must be able to build every screen from that data
before local inference is ready.

### Scope invariant

`soul.md` remains the product feature source of truth. This three-person plan redistributes its full
hackathon scope; it does not authorize the old scope-cut list or remove Tauri, multi-repo, voice,
overflow, self-adjustment, hosted fallback, any maintainer task type, or any evidence requirement.
When blocked, expose the agreed mock/seed boundary so the other members continue, then finish the
real integration and acceptance test before declaring this lane done.

## What the other two members own

### Member 1 — Runtime and Intelligence

Member 1 owns `runtime/`, `agents/`, and `evals/`. They claim tasks from your HTTP interface,
execute the Planner and specialist DAG, manage llama.cpp models and worktrees, call Linkup, generate
typed artifacts, run the critic, and send credential-free write-back intents. They supply the command
that your GitHub Actions eval workflow executes.

### Member 3 — Operator Experience and Demo

Member 3 owns `apps/dashboard/`, `apps/desktop/`, `apps/docs/`, and `evidence/`. They consume your
Convex queries and mutations for live traces, search, diff, cost analytics, agents, Role Builder,
review queue, evals, policies, prompts, pause controls, alerts, and voice. They own browser audio and
recording; you own secret-bearing ElevenLabs actions.

## Repository ownership

You may edit these paths without coordination:

```text
convex/
apps/worker/
packages/contracts/
policy/
infra/
scripts/                         # root bootstrap, seed, health and demo scripts
.github/
package.json
pnpm-workspace.yaml
pnpm-lock.yaml
.env.example
.gitignore
README.md                        # only root setup/run instructions
```

Do not directly edit:

```text
runtime/                         # Member 1
agents/                          # Member 1
evals/                           # Member 1
apps/dashboard/                  # Member 3
apps/desktop/                    # Member 3
apps/docs/                       # Member 3
evidence/                        # Member 3
```

You are the owner of shared contracts. That does not mean you may change them unilaterally. For any
field change, receive Member 1's Pydantic impact and Member 3's UI impact, bump `schemaVersion` when
the change is breaking, update JSON fixtures, and obtain acknowledgement from both members before
merging.

## Shared product layout and root commands

The merged repository must have this layout:

```text
Hermes/
├─ agents/                       # Member 1
├─ apps/
│  ├─ dashboard/                 # Member 3
│  ├─ desktop/                   # Member 3
│  ├─ docs/                      # Member 3
│  └─ worker/                    # you
├─ convex/                       # you
├─ evals/                        # Member 1
├─ evidence/                     # Member 3
├─ infra/                        # you
├─ packages/contracts/           # you
├─ policy/                       # you
├─ runtime/                      # Member 1
├─ scripts/                      # you
├─ .github/workflows/            # you
├─ .env.example                  # you
├─ package.json                  # you
└─ pnpm-workspace.yaml           # you
```

Implement these root commands. They are part of your acceptance criteria, not optional polish:

```bash
pnpm dev               # Convex dev + Worker dev + dashboard + Python runtime
pnpm dev:convex
pnpm dev:worker
pnpm dev:dashboard
pnpm dev:runtime
pnpm build             # contracts, Convex typecheck, Worker, dashboard, docs, Python compile
pnpm test              # all TypeScript tests plus pytest and fast Gauntlet
pnpm test:contracts
pnpm test:integration
pnpm demo:seed         # seed all UI/demo scenarios
pnpm demo:check        # verify endpoints, models, GitHub, Cloudflare, Convex and env
pnpm deploy:worker
pnpm deploy:dashboard
pnpm deploy:docs
```

Use Node.js 22, pnpm workspaces, Python 3.12, and `concurrently` for local orchestration. If a service
is intentionally disabled, `pnpm demo:check` must say exactly which feature is unavailable rather
than returning a vague failure.

## Shared contract package

Create:

```text
packages/contracts/
├─ package.json
├─ tsconfig.json
├─ src/
│  ├─ ids.ts
│  ├─ task.ts
│  ├─ plan.ts
│  ├─ artifact.ts
│  ├─ trace.ts
│  ├─ agent.ts
│  ├─ policy.ts
│  ├─ memory.ts
│  ├─ eval.ts
│  ├─ alert.ts
│  ├─ writeback.ts
│  └─ index.ts
└─ fixtures/
   ├─ task.json
   ├─ run.json
   ├─ plan.json
   ├─ artifacts.json
   ├─ spans.json
   ├─ agents.json
   ├─ eval-run.json
   └─ alert.json
```

Use explicit discriminated unions for task source/type/status, artifact type, span status, critic
verdict, write-back action, alert channel, and agent origin. Use Unix epoch milliseconds everywhere.
Use opaque string IDs with prefixes (`task_`, `run_`, `span_`, `artifact_`, `agent_`, `eval_`). Never
let UI code infer semantics from a raw Convex `_id`.

### Minimum task contract

```ts
type TaskStatus =
  | "pending"
  | "claimed"
  | "running"
  | "done"
  | "failed"
  | "escalated";

type Task = {
  schemaVersion: 1;
  taskId: string;
  source: "github" | "ui" | "voice" | "eval";
  type: "intake" | "triage" | "classify" | "dedupe" | "clarify" | "label" |
        "respond" | "repro" | "fix" | "review" | "docs" | "release" |
        "role_test" | "escalate";
  repo: string;
  payload: Record<string, unknown>;
  status: TaskStatus;
  dedupeKey: string;
  approvedBacklogBatchId?: string;
  lease?: { leaseId: string; owner: string; expiresAt: number };
  resultUrls: string[];
  createdAt: number;
  updatedAt: number;
};
```

The fixtures are the cross-language contract test. Member 1 validates them with Pydantic; Member 3
imports the TypeScript package. Do not duplicate UI-specific interfaces in the dashboard.

## Convex data model

Implement indexes for every query Member 3 needs. Do not rely on full table scans for the run list.

### `tasks`

Fields:

```text
taskId, source, type, repo, payload, status, dedupeKey, approvedBacklogBatchId?,
leaseId?, leaseOwner?, leaseExpiresAt?, heartbeatAt?,
resultUrls[], error?, createdAt, updatedAt
```

Indexes:

```text
by_task_id
by_status_created_at
by_repo_status
by_dedupe_key
by_updated_at
```

### `runs`

```text
runId, taskId, repo, lane, status, plannerConfidence?, planArtifactId?,
startedAt, finishedAt?, totalTokensIn, totalTokensOut,
totalCostUsd, totalCloudEquivalentUsd, totalLatencyMs,
agentVersions, resultUrls[], fallbackFlags[], error?
```

Indexes: `by_run_id`, `by_task_id`, `by_started_at`, `by_repo_started_at`, `by_status`.

### `spans`

Store the complete span contract from Member 1, including parent, node, agent/version, model,
prompt hash, artifact refs, tokens, actual/equivalent cost, latency, tools, verdict and error.

Indexes: `by_run_started_at`, `by_run_parent`, `by_agent_started_at`, `by_status_started_at`.

### `artifacts`

```text
artifactId, runId, nodeId, type, schemaVersion, producer,
upstreamArtifactIds[], policyRuleIds[], content, contentText,
createdAt, contentHash
```

`contentText` is a redacted/searchable projection. Never index secrets or raw untrusted binary data.

### `agents`

```text
agentId, name, version, origin(kickoff|spawned|role_builder), spawnedByRunId?,
job, persona, baseWeights, tools[], guardrails,
state(draft|tested|active|inactive), draftHash, testFlightRunId?, active,
createdAt, supersedes?
```

Keep all versions. `name + version` must be unique.

### `entities`

```text
entityId, kind(user|issue|repo), key, snapshot, history[], updatedAt
```

Use separate projections for context packing; do not send unbounded history to the runtime.

### `policies`

```text
policyId, path, version, yaml, parsed, gitSha, active, updatedAt
```

### `evalCases` and `evalRuns`

Store source, status, input, golden, wrong output, corrected output, scorer, tags, case version,
per-case result, aggregate thresholds, agent versions, CI URL and Git SHA.

### `alertRules` and `alertEvents`

Rules contain type, enabled flag, predicate parameters, severity and channels. Events contain rule,
run, message, observed value, baseline, fired time, acknowledgement and optional voice asset ref.

### `writebackActions`

```text
actionId, taskId, runId, idempotencyKey, actionType, repo,
requestHash, policyDecision, status, resultUrl?, responseSummary?, error?,
createdAt, completedAt?
```

This table is the audit trail and the source of truth for exactly-once GitHub effects.

### `repositories`

```text
repo, githubRepositoryId, installationId, defaultBranch,
writebackOptIn, allowedActions[], protectedPaths[], sizeLimits,
requiredChecks[], activePolicyVersion, lastWebhookAt?, health, updatedAt
```

Only server actions may read repository/installation IDs. Dashboard queries return a redacted health
projection without GitHub numeric IDs, tokens or secret references.

### `systemState`

Store global pause, per-agent pause, emergency mode, write-back mode, current agent tag, and updated
time. All dangerous write-back code checks this table immediately before acting.

## Convex functions and HTTP boundary

Use small modules rather than a single oversized file:

```text
convex/
├─ schema.ts
├─ http.ts
├─ auth.ts
├─ tasks.ts
├─ runs.ts
├─ spans.ts
├─ artifacts.ts
├─ agents.ts
├─ entities.ts
├─ policies.ts
├─ evalCases.ts
├─ evalRuns.ts
├─ alerts.ts
├─ system.ts
├─ repositories.ts
├─ github.ts
├─ voice.ts
├─ seeds.ts
└─ lib/
   ├─ ids.ts
   ├─ validation.ts
   ├─ redaction.ts
   ├─ idempotency.ts
   ├─ policyEngine.ts
   └─ githubApp.ts
```

### Runtime HTTP actions

All `/runtime/*` endpoints require a constant-time comparison against `HELIOS_RUNTIME_TOKEN`, reject
oversized bodies, validate schema versions, and accept `Idempotency-Key`.

```text
POST /runtime/claim
  input:  { instanceId, capabilities[], now }
  output: task + memoryPack + policyPack + lease

POST /runtime/heartbeat
  input:  { taskId, leaseId, instanceId, progress }
  output: { accepted, leaseExpiresAt, paused }

POST /runtime/run/start
  input:  run metadata
  output: canonical run record

POST /runtime/span
  input:  span event
  output: { accepted, duplicate }

POST /runtime/artifact
  input:  typed artifact
  output: { accepted, duplicate, artifactId }

POST /runtime/run/finish
  input:  terminal status and aggregates
  output: canonical totals and capture-eval decision

POST /runtime/task/escalate
  input:  escalation artifact and artifact chain
  output: review queue identifier

POST /runtime/writeback
  input:  critic-passed write-back intent
  output: action status and resulting GitHub URLs

GET /runtime/control
  output: global/per-agent pause, emergency mode and write-back mode
```

Return `409` for lost leases or idempotent replays, `422` for contract validation, `429` for bounded
rate limiting, and structured `5xx` errors with retryability. Never return HTML error pages.

### Dashboard queries and mutations

Expose native Convex APIs with stable names:

```text
tasks.list, tasks.get, tasks.enqueueFromUi
tasks.validateApprovedBacklog, tasks.enqueueApprovedBacklog
runs.list, runs.get, runs.compare
spans.listByRun
artifacts.listByRun, artifacts.get
agents.list, agents.getVersions, agents.createRoleDraft, agents.createVersionDraft
agents.startTestFlight, agents.activateVersion, agents.setActive
entities.getForOperator
policies.list, policies.validateDraft, policies.saveDraft
evalCases.list, evalCases.approve, evalCases.reject
evalRuns.list, evalRuns.get, evalRuns.start
alerts.listRules, alerts.saveRule, alerts.listEvents, alerts.acknowledge
system.get, system.setGlobalPause, system.setAgentPause, system.setWritebackMode
repositories.listHealth
reviews.list, reviews.get, reviews.approve, reviews.editAndApprove, reviews.reject
analytics.costByAgent, analytics.latencyByType, analytics.modelTimeline
```

Queries must return operator-safe redacted data. Secret values, GitHub installation tokens, webhook
signatures and private keys never enter query results.

Role Builder uses durable runtime tasks rather than calling localhost from the public browser:

1. `agents.createRoleDraft` stores the safe tool/guardrail selections and enqueues a `role_test` task
   with `payload.stage = "persona_draft"`; Member 1 returns a versioned persona artifact.
2. `agents.startTestFlight` enqueues a second `role_test` task with
   `payload.stage = "test_flight"`, the immutable draft ID and an approved canned task ID. It always
   uses dry-run/no-GitHub grants.
3. `agents.activateVersion` succeeds only after a passing test-flight run for the exact draft hash,
   registers `origin: role_builder`, and writes an audit event. Editing the draft invalidates the
   prior test flight.
4. `evalRuns.start` similarly enqueues an `eval`-source task/tag request; the dashboard subscribes to
   the resulting eval run. The browser never receives `HELIOS_LOCAL_API_TOKEN`.

The prompt editor uses `agents.createVersionDraft` for an existing role. It stores an immutable
persona diff and proposed version without changing the active pointer. `agents.activateVersion`
requires a passing full Gauntlet for that exact draft hash and current policy/case-set versions;
otherwise it returns the blocking eval run instead of activating.

### Approved backlog release for the overflow demo

Preserve the backlog-drain feature from `soul.md`, but make it operate on real work and resist spam.
`tasks.validateApprovedBacklog` accepts at most 25 existing GitHub issue URLs and returns, per URL:
repository, issue number/title, open/closed state, allowlist status, prior Hermes task/result, and a
specific rejection reason. It performs no enqueue or GitHub write.

`tasks.enqueueApprovedBacklog` requires the operator to submit the unchanged validated list plus an
explicit confirmation. Revalidate immediately before enqueue, require every repository to be in
`GITHUB_ALLOWED_REPOS`, reject closed issues, bot-created demo loops, duplicate queue entries, and
issues Hermes already completed, and assign one immutable `approvedBacklogBatchId`. Enqueue the
original issue payload and URL; never fabricate, clone, or rewrite an issue to increase the counter.
Return accepted task IDs and rejected URLs separately so the UI cannot imply all work was accepted.

The completed-real-task counter increments only when a task reaches a terminal GitHub action with a
persisted result URL. Fixture, dry-run, failed, cancelled and merely queued tasks never count. Store
batch progress so Member 3 can show `queued → running → completed/escalated` during judging. The
operator can stop future claims through global pause, but already-issued GitHub actions remain in the
immutable audit log.

## Task leases and crash safety

Implement task claim as one atomic mutation:

1. Select the oldest compatible `pending` task.
2. Also consider `claimed/running` tasks whose lease has expired.
3. Set status, owner, random lease ID, expiry and heartbeat.
4. Return task plus bounded memory/policy packs.

Heartbeat accepts only the current lease ID and owner. A late process cannot revive an expired lease.
A scheduled function periodically requeues expired work and records an alert. Task completion must
verify the lease one final time.

## GitHub webhook Worker

Create:

```text
apps/worker/
├─ src/index.ts
├─ src/github/verify.ts
├─ src/github/normalize.ts
├─ src/github/events.ts
├─ src/convex.ts
├─ src/status.ts
├─ src/inference.ts
├─ test/webhook.test.ts
├─ test/inference.test.ts
├─ wrangler.toml
└─ package.json
```

The Worker must:

1. Read the raw request body before parsing JSON.
2. Verify `X-Hub-Signature-256` using Web Crypto and `GITHUB_WEBHOOK_SECRET`.
3. Reject missing/invalid signatures with `401` and no leaked detail.
4. Use `X-GitHub-Delivery` plus action/repo as the dedupe key.
5. Normalize `issues`, `issue_comment`, `pull_request`, `pull_request_review`, `workflow_run`, and
   release-related events into the shared task contract.
6. Ignore bot-authored loops and events created by Hermes's own write-back marker.
7. Enqueue through an authenticated Convex HTTP action.
8. Respond within GitHub's timeout; never wait for inference.
9. Expose `/health` and a minimal public status response without internal details.

Also expose authenticated `POST /inference/fallback`. It accepts only the bounded planner request
contract agreed with Member 1, rejects arbitrary URLs/tools and excessive context/output limits, and
tries configured providers in this order: Workers AI, then the configured Haiku-compatible model.
Return provider, exact model, output, input/output token counts, latency, actual USD cost and request
ID. Use the Workers AI binding and provider key only inside the Worker. Never log prompt bodies,
authorization headers or provider responses containing sensitive issue text. Apply per-instance rate
limits and return a structured retryable error when no provider succeeds; do not invent a response.

Add a poller fallback scheduled action for missed GitHub events in the demo repository.

## Credentialed GitHub write-back service

Only your Convex action layer holds GitHub App credentials. The runtime and browser never receive an
installation token.

Support these action types:

```text
comment
labels_set
milestone_set
duplicate_close
branch_and_pr
pr_review_comment
pr_merge
release_draft
policy_commit
eval_case_commit
```

### Mandatory enforcement before every action

- Repository is in `GITHUB_ALLOWED_REPOS`.
- Global and relevant agent pause switches are off.
- `HELIOS_WRITEBACK_MODE` permits the requested action.
- Critic verdict is `pass` and references the artifact hash.
- Idempotency key has not completed before.
- The current base SHA is compatible with the intent.
- Action is within per-task limits.
- Protected paths and security labels trigger escalation.
- Deterministic content checks reject secrets, prohibited profanity/harassment and drafts marked with
  angry-user or unsupported-security-claim risk; rejection creates a context-complete review item.
- Autonomous merges meet patch-size, CI, security, critic and policy conditions.
- Force-push, branch deletion, settings changes, secret access and release publication are rejected
  in code, regardless of prompt content.

### Creating a PR without sharing credentials

Member 1 supplies a patch artifact containing full post-change file contents and `base_sha`. Use the
GitHub Git Data API:

1. Get base commit and tree.
2. Create blobs for changed files.
3. Create a new tree based on the base tree.
4. Create a commit with the approved message.
5. Create an idempotent `hermes/<task>-<slug>` ref.
6. Open or reuse the PR.
7. Persist commit, branch and PR URLs.

If the base SHA moved or the same path changed, stop and return a rebase-required escalation; do not
silently overwrite another contributor's work.

### Merge policy

All features remain implemented, including autonomous merge, but live mode must be policy-gated.
Require green required checks, no protected paths, no security issue, diff below line limit, critic
pass, security artifact clean, branch up to date, and explicit repository opt-in. Otherwise keep the
PR open and create a review item. Releases are draft-only; publication is always forbidden.

## Multi-repository onboarding and isolation

Onboard both the Hermes repository and one second real repository with organic history before the
integration freeze. For each repository, record GitHub installation/repository ID, default branch,
write-back opt-in, allowed autonomous actions, protected paths, size limits, required checks and
active policy version. A string in `GITHUB_ALLOWED_REPOS` alone is not onboarding.

Use `repo` in every task/run/entity/policy/write-back lookup and idempotency key. GitHub installation
tokens must be minted for the matching installation/repository only. Reject payload/repository ID
mismatches even when the human-readable owner/name is allowlisted. Test colliding issue numbers and
delivery IDs across both repositories. Provide Member 3 a read-safe repository health/config query so
the Settings page proves both are connected without exposing installation IDs or secrets.

Second-repo acceptance test: a genuine webhook enters under the correct repo, receives only that
repo's memory/policy pack, completes a safe comment/label or PR action, and exposes its real GitHub URL
in the dashboard. Keep the two-repo evidence run IDs and URLs.

## Three-layer memory and policy persistence

### Layer 1 — now

Artifacts and run state are already stored by run ID. Return only relevant artifact refs on resume.

### Layer 2 — entity history

After a terminal run, update user, issue and repository entity snapshots in the same logical workflow
as run completion. Maintain concise summaries plus structured facts; keep raw history separately.
Build a context pack with strict item and byte limits.

### Layer 3 — policy

Own and seed:

```text
policy/triage.yaml
policy/autonomy.yaml
policy/escalation.yaml
policy/voice.yaml
```

Every rule has a stable ID, description, parameters, severity and version. Validate YAML before
activation. Policy UI edits create a Git commit through the same write-back service, update the
Convex mirror only after GitHub succeeds, and retain the old version.

Encode the full autonomy boundary from `soul.md`, not a shortened demo policy:

- Autonomous after critic pass: classification, priority, labels, milestones, clarification and
  answer comments, exact-duplicate closure above threshold, fix PR opening, inbound PR review
  comments, docs-only merge with green CI, qualifying small-code merge, and release **draft**.
- Escalate by exception: security-labelled work, breaking API changes, protected paths, planner
  confidence below policy, two critic rejections, any budget breach, angry-user sentiment,
  repository/base-SHA conflict, or required provider/tool outage.
- Hard-never in executable code: force-push, branch deletion, repository/settings changes, secret
  access, release publication, a write to a non-allowlisted repository, or exceeding spend/action
  limits. No prompt, role setting, critic verdict or operator UI payload can override these rules.

The merge gate for qualifying code and docs remains the stricter deterministic check in the
write-back section; “autonomous” never means “skip CI/security/policy.”

## Evaluation and closed-loop capture

Member 1 owns cases/scoring. You own persistence, capture triggers and CI enforcement.

Capture a `pending-review` eval case when:

- The critic blocks or a run fails.
- A task escalates.
- A human edits or rejects an outbound artifact.
- A maintainer changes Hermes-applied labels.
- A maintainer edits/corrects a Hermes reply.
- A Hermes PR is reverted or receives a failure label.

Store input, wrong output, correction, relevant policy/agent versions, and source URL. Member 3's UI
approves the case; your write-back service commits the approved fixture to `evals/gauntlet/`.

Create `.github/workflows/eval.yml`:

1. Trigger for changes under `agents/**`, `policy/**`, `runtime/**`, or `evals/**`.
2. Install Python 3.12 and runtime dependencies.
3. Run `python -m helios.evals.run --ci`.
4. Upload JSON report.
5. Fail below overall 85%, triage 85%, response 85%, or fix 70%.
6. Post/retain a concise check summary.

Configure branch protection manually and keep one genuine blocked PR as evidence. Persist and pin
three consecutive complete `agents-v4` Gauntlet runs at ≥85% overall with the identical case-set
version; Member 3 links all three from the eval dashboard.

## Alerts and ElevenLabs

Implement scheduled alert evaluation for:

- Task or run failure.
- Lease expiry.
- Cost greater than four times task-type baseline.
- Latency greater than twice baseline.
- Escalation creation.
- Eval regression.
- Model server unavailable.

Create dashboard events immediately. For voice-enabled alerts, call ElevenLabs server-side, store a
short-lived asset reference or byte response, and let Member 3 play it. Rate-limit repeated voice
alerts and dedupe on `rule + run`.

Expose actions for:

```text
voice.transcribeAssignment(audio) → transcript + normalized task draft
voice.synthesizeAlert(message) → playable audio
voice.generateStandup(dateRange) → text + playable digest
```

Never expose `ELEVENLABS_API_KEY` to the browser. Validate audio size and content type.

Wispr Flow requires no backend integration; Member 3 owns field compatibility and evidence capture.

## Environment and secrets

Your `.env.example` documents all variables but contains no real values:

```text
# Shared/local
CONVEX_DEPLOYMENT=
CONVEX_URL=
CONVEX_HTTP_URL=
HELIOS_RUNTIME_TOKEN=
HELIOS_WRITEBACK_MODE=dry-run
HELIOS_DEMO_MODE=1

# Browser-safe only
VITE_DATA_MODE=convex
VITE_CONVEX_URL=
VITE_WORKER_URL=http://127.0.0.1:8787
VITE_RUNTIME_URL=http://127.0.0.1:8788
VITE_GITHUB_REPO_URL=
VITE_DOCS_URL=
VITE_DEMO_MODE=1
VITE_ENABLE_VOICE=1
VITE_ENABLE_TAURI=1

# GitHub App — server only
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_BASE64=
GITHUB_INSTALLATION_ID=
GITHUB_WEBHOOK_SECRET=
GITHUB_ALLOWED_REPOS=owner/hermes,owner/second-repo
GITHUB_HERMES_BOT_LOGIN=

# Cloudflare — deployment/Worker only
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
WORKER_CONVEX_INGEST_TOKEN=
FALLBACK_PROVIDER_ORDER=workers-ai,haiku
WORKERS_AI_MODEL=
WORKERS_AI_PRICING_JSON=
ANTHROPIC_API_KEY=
ANTHROPIC_HAIKU_MODEL=
HAIKU_INPUT_USD_PER_MILLION=
HAIKU_OUTPUT_USD_PER_MILLION=

# Voice — server only
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# Runtime variables documented for Member 1
HELIOS_INSTANCE_ID=demo-laptop-1
HELIOS_API_HOST=127.0.0.1
HELIOS_API_PORT=8788
HELIOS_LOCAL_API_TOKEN=
HELIOS_CORS_ORIGINS=http://localhost:5173
HELIOS_WORKSPACE_ROOT=./workspace
HELIOS_OUTBOX_PATH=./workspace/outbox.jsonl
HELIOS_MAX_VRAM_MB=7600
HELIOS_FAST_LANE_TIMEOUT_S=55
HELIOS_DEEP_LANE_TIMEOUT_S=480
HELIOS_MAX_PARALLEL_NODES=3
HELIOS_FALLBACK_MODE=worker
HELIOS_FALLBACK_URL=http://127.0.0.1:8787/inference/fallback
LLAMA_PLANNER_URL=http://127.0.0.1:8081
LLAMA_TRIAGE_URL=http://127.0.0.1:8082
LLAMA_CODER_URL=http://127.0.0.1:8083
LLAMA_EMBED_URL=http://127.0.0.1:8084
LINKUP_API_KEY=
GIT_REPO_CACHE_ROOT=./workspace/repos
```

Add secret-scanning patterns and ensure logs redact PEM material, installation tokens, API keys,
webhook signatures, authorization headers, issue content marked private, and potential secrets from
patches.

## Cloudflare responsibilities

- Deploy the GitHub webhook Worker and verify request logs during a real event.
- Help Member 3 deploy dashboard and docs projects to Pages; they own UI/build config, you own account
  bindings, domains and secrets.
- Configure Workers AI fallback variables if Member 1 enables it.
- Keep Haiku-compatible credentials optional and server-only; the Worker must return measured token
  usage and configured actual cost for either hosted provider.
- Provide live URLs and a one-command redeploy path.
- Test from the venue network and phone hotspot.
- Do not make the local runtime directly reachable from the public internet.

## Hour-by-hour execution plan

### Hours 0–2 — Monorepo, contracts and hosted services

- Create pnpm workspace, root scripts, contracts package, fixtures and `.env.example`.
- Initialize Convex schema/project and Worker skeleton.
- Create GitHub App, demo repository allowlist and webhook secret.
- Give Member 1 runtime endpoint fixtures and Member 3 generated Convex types plus seed fixtures.
- Establish `integration` branch and required checks.

**Handoff at hour 2:** installable monorepo, contract fixtures, Convex deployment URL, Worker health
URL, and fake data query.

### Hours 2–6 — Durable vertical slice

- Implement task enqueue, claim, lease, heartbeat, run/span/artifact persistence and finish.
- Implement Worker signature verification and issue normalization.
- Implement comment/labels write-back with dry-run and live modes.
- Seed one fake runtime run for Member 3.
- Integrate Member 1's in-memory/real adapter against your HTTP endpoints.

**Exit test:** real GitHub issue webhook creates one task; a deterministic fake runtime finishes it;
comment and labels land once.

### Hours 6–10 — Complete trace/control APIs

- Add all data tables, indexes, queries and redaction.
- Add result URLs, write-back audit, idempotency and lost-lease behavior.
- Add global/per-agent pause and emergency write-back switch.
- Support the fast lane's duplicate close and substantive reply actions.
- Confirm live Convex subscriptions update Member 3's dashboard.

### Hours 10–16 — Deep-lane GitHub work

- Implement branch/commit/PR creation from Member 1's patch artifact.
- Implement PR review comments, merge policy gate and draft releases.
- Implement protected paths, line limits, required check verification and allowlist enforcement.
- Add policy commit and eval-case commit actions.
- Test base-SHA conflict and idempotent retry behavior.

**Exit test:** Member 1's tested patch artifact produces a real PR without exposing credentials.

### Hours 16–21 — Memory, agents, policies and emergent org persistence

- Implement entity memory snapshots/history and bounded context packs.
- Implement agent registry with kickoff, spawned and Role Builder origins plus version history.
- Persist spawn birth events and persona adjustment diffs.
- Mirror policies from Git and serve active packs to the runtime.
- Onboard and exercise the second real repository with per-repo policy and write-back settings.
- Implement review/escalation queue and approve/edit/reject mutations.

### Hours 21–27 — Evals, alerts, voice and power-ups

- Implement closed-loop eval capture and approval-to-Git commit.
- Add eval-run storage and CI workflow with blocking thresholds.
- Add alert rules, scheduled evaluation and event log.
- Add ElevenLabs alert, assignment transcription and standup actions.
- Deploy Worker and help deploy Pages projects.
- Configure and test the Worker fallback ladder without exposing either provider secret to runtime
  files or UI.
- Implement validated approved-backlog batches and seed one clearly labelled fixture batch for UI
  work; only genuine issue URLs may be used for final evidence.

### Hours 27–31 — Security, outage and rate-limit hardening

- Test invalid signatures, replayed deliveries, self-generated webhook loops and oversized payloads.
- Test expired leases, duplicate spans/artifacts, duplicate GitHub actions and partial GitHub failure.
- Test Convex/Cloudflare/GitHub/ElevenLabs outages and bounded retry behavior.
- Verify all logs and UI projections are redacted.
- Add local buffering or explicit degraded-mode signals where cloud connectivity is unavailable.

### Hours 31–34 — Integration freeze and deployment

- Merge root/config/contracts first, then Member 1 runtime, then Member 3 UI.
- Run `pnpm build`, `pnpm test`, `pnpm demo:seed` and `pnpm demo:check` from a clean clone.
- Freeze schemas unless a blocker affects the demo.
- Confirm production environment variables and GitHub App permissions.
- Export/back up Convex seed data and evidence run identifiers.

### Hours 34–36 — Rehearsal operations

- Run two full issue-to-reply and one issue-to-PR flows.
- Trigger one honest alert and retain it.
- Verify the CI-blocked eval PR, spawned agent run, critic revision run and escalation item.
- During judging, monitor Worker requests, Convex tasks/leases and GitHub rate limits.
- You own the emergency transition between `live`, `pr-only`, and `dry-run` write-back modes.

## Required tests

### Contracts and persistence

- TypeScript fixtures validate and Member 1's Pydantic contract suite passes.
- Required indexes support every dashboard list query.
- Unknown schema versions and oversized content fail clearly.
- Artifact search projection is redacted and bounded.

### Webhooks

- Valid signature accepted; invalid/missing signature rejected.
- Replayed `X-GitHub-Delivery` creates exactly one task.
- Hermes-authored comments do not create infinite tasks.
- Supported event types normalize into stable task payloads.
- Worker returns promptly even when Convex is temporarily unavailable.

### Backlog and hosted inference

- Backlog validation rejects non-allowlisted, closed, duplicate, bot-loop and already-completed
  issues; enqueue revalidates and creates one traceable batch.
- Completed-real-task aggregates require a terminal persisted GitHub URL and exclude fixtures,
  dry-runs and queue-only records.
- Fallback rejects missing runtime auth, oversized requests, arbitrary tools/URLs and invalid output
  schemas.
- Workers AI failure either advances to the configured Haiku-compatible provider or returns a
  structured failure; provider/model/tokens/latency/actual cost are always persisted honestly.

### Leases and runtime APIs

- Only one instance claims a task.
- Heartbeat extends the correct lease.
- Expired tasks requeue exactly once.
- Lost owner cannot complete or write back.
- Replayed span/artifact calls are idempotent.

### Write-back safety

- Disallowed repos, protected paths, failed critic, failed CI and oversized patches block.
- Same idempotency key returns the original GitHub URL.
- Base-SHA conflicts escalate rather than overwrite.
- Force-push, branch deletion, settings edits, secret access and release publication are impossible.
- Dry-run creates a complete audit record without GitHub mutation.
- Unsafe reply fixtures are blocked by code even if the critic payload claims `pass`.

### Memory, policy and evals

- Run completion updates all relevant entity memories.
- Context packs respect byte/history limits.
- Colliding issue numbers across two repos return only the matching repo memory and policy.
- Invalid policy YAML never becomes active.
- UI policy edit commits to Git before changing the active Convex mirror.
- Human correction creates a pending eval case.
- CI fails below thresholds and exposes its report URL.

### Alerts and voice

- Failure, cost, latency, escalation, lease and eval rules fire once.
- Voice alerts are rate-limited and contain no secret/private content.
- Audio upload limits and invalid formats are rejected.
- ElevenLabs outage leaves a visible text alert and does not fail the run.

### Merge/run

- Fresh-clone setup reaches a healthy `pnpm dev` state.
- `pnpm build` and `pnpm test` return zero.
- `pnpm demo:seed` is repeatable and idempotent.
- `pnpm demo:check` identifies every configured external surface.

## Member 2 definition of done

- Convex is the source of truth for tasks, runs, spans, artifacts, agents, memories, policies, evals,
  alerts, reviews and system state.
- Cloudflare Worker accepts genuine GitHub webhooks with HMAC verification.
- The approved backlog release queues only validated real issues and reports verifiable batch
  progress without inflating the completed counter.
- The authenticated Worker fallback preserves the Workers AI → Haiku-compatible ladder and never
  exposes provider credentials.
- Runtime claims and resumes work through authenticated, idempotent endpoints.
- GitHub comments, labels, closures, branches, PRs, merges under policy, policy commits, eval commits
  and draft releases work without sharing credentials.
- Three memory layers and versioned policies are served to Member 1.
- Spawned and Role Builder agents persist with origin/version history.
- Closed-loop failures become reviewable eval cases; CI genuinely blocks regressions.
- Alerts fire, remain searchable, and optionally speak through ElevenLabs.
- Dashboard and docs are deployed on Cloudflare Pages with Member 3.
- Root install/dev/build/test/seed/check commands work from a clean clone.
- Every external mutation has an idempotency key, policy decision and result URL.

## Merge and handoff checklist

1. Work on `member2/control-plane`; you are the only member editing root integration files.
2. Publish contracts and fixtures by hour 2 and tag contract checkpoints.
3. Merge to `integration` at hours 6, 16, 27 and 31 after tests pass.
4. Before every integration merge, run:

   ```bash
   pnpm test:contracts
   pnpm --filter worker test
   pnpm convex dev --once
   pnpm test:integration
   ```

5. Give Member 1 endpoint/contract changes before merging them.
6. Give Member 3 query/mutation names and seed IDs before merging them.
7. Never fix another member's code directly during freeze; provide exact failing input and expected
   contract unless all three agree on an emergency paired fix.
8. Final merge order is root/contracts/control plane, runtime, dashboard/docs/desktop, then only
   conflict-resolution commits.
9. Validate the final system from a clean clone and a second machine or Windows user profile.
