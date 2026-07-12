# Team Member 1 — Helios Runtime, Models, Agents, and Evaluation

## Mission

You own the entire on-device execution plane. Your job is to turn a claimed task plus its
memory and policy pack into a validated artifact that Member 2 can safely write to GitHub and
Member 3 can explain visually. You are responsible for the part of the demo that proves Hermes
is an agency rather than a dashboard: a manager creates a task-specific plan, specialist agents
execute it, a critic rejects or accepts the work, and the result is supported by tests and a
complete trace.

Your work must function without the real Convex backend by using an in-memory control-plane
adapter. That rule is important: you may integrate with Member 2 as soon as their HTTP endpoints
exist, but you must never wait for them before developing or testing the runtime.

### Scope invariant

`soul.md` remains the product feature source of truth. This three-person plan redistributes its full
hackathon scope; it does not authorize the old scope-cut list or remove Tauri, multi-repo, voice,
overflow, self-adjustment, hosted fallback, any maintainer task type, or any evidence requirement.
When blocked, use the documented fixture/degraded adapter and raise an integration issue, but keep the
real implementation and acceptance test on this plan.

## What the other two members own

### Member 2 — Control Plane and Integrations

Member 2 owns `convex/`, `apps/worker/`, `packages/contracts/`, `policy/`, `.github/`, root
workspace scripts, GitHub App authentication, the credentialed write-back service, task leases,
memory persistence, alert rules, Cloudflare configuration, and ElevenLabs server-side calls.
They expose authenticated HTTP endpoints to you. You never store or request GitHub private keys.

### Member 3 — Operator Experience and Demo

Member 3 owns `apps/dashboard/`, `apps/desktop/`, `apps/docs/`, and `evidence/`. They display your
plans, spans, artifacts, model load events, costs, failures, critic revisions, spawned experts,
and eval results. They also own the Role Builder UI, review queue, policy and prompt editors,
voice assignment UI, Tauri shell, public docs site, and demo choreography.

## Repository ownership

You may edit these paths without coordination:

```text
runtime/
  pyproject.toml
  src/helios/
  tests/
  fixtures/
agents/
evals/
  gauntlet/
  snapshots/
  reports/
```

Do not directly edit these paths:

```text
convex/                 # Member 2
apps/worker/            # Member 2
packages/contracts/     # Member 2; propose changes before they edit it
policy/                 # Member 2; you only consume the policy pack
.github/                # Member 2; provide the command CI must invoke
apps/dashboard/         # Member 3
apps/desktop/           # Member 3
apps/docs/              # Member 3
evidence/               # Member 3
package.json            # Member 2 is the integration owner
pnpm-workspace.yaml      # Member 2
.env.example             # Member 2; send them any required variable additions
```

If a shared contract must change, post the exact field change and one example payload in the
team channel. Member 2 changes the TypeScript contract, you update the Pydantic mirror and
contract fixtures, and Member 3 updates the consumer. Do not merge a contract change until all
three acknowledge it.

## Shared product architecture

The merged repository is expected to have this shape:

```text
Hermes/
├─ agents/                       # your versioned expert definitions
├─ apps/
│  ├─ dashboard/                 # Member 3
│  ├─ desktop/                   # Member 3
│  ├─ docs/                      # Member 3
│  └─ worker/                    # Member 2
├─ convex/                       # Member 2
├─ evals/                        # your cases and evaluator
├─ evidence/                     # Member 3
├─ packages/contracts/           # Member 2, shared source of truth
├─ policy/                       # Member 2, consumed by your planner/gates
├─ runtime/                      # your Python package
├─ .github/workflows/            # Member 2
├─ .env.example                  # Member 2
├─ package.json                  # Member 2
└─ pnpm-workspace.yaml           # Member 2
```

The normal development command after all branches merge must be:

```bash
pnpm install
python -m pip install -e "runtime[dev]"
pnpm dev
```

Member 2 owns `pnpm dev`; your responsibility is to make this command work reliably:

```bash
python -m helios.main                    # starts poller, scheduler and local FastAPI :8788
```

In `runtime/pyproject.toml`, require Python 3.12+ and declare runtime dependencies for FastAPI,
Uvicorn, Pydantic/settings, HTTPX, psutil, YAML parsing and the Linkup client. Put pytest,
pytest-asyncio, coverage, Ruff and type checking in the `dev` extra used above. Keep llama.cpp as an
external executable/model prerequisite checked by bootstrap rather than pretending it is installed by
pip. Expose console scripts for `helios-runtime`, `helios-health` and `helios-evals`, while retaining
the `python -m` entry points used by root automation.

Your package must also expose:

```bash
python -m helios.models.bootstrap      # inspect hardware and start/verify llama.cpp servers
python -m helios.evals.run             # run the complete Gauntlet
python -m helios.evals.run --fast      # fast CI subset
python -m helios.evals.run --ci        # threshold-enforcing full CI mode
python -m helios.demo.seed_runtime     # create deterministic saved traces for UI development
python -m helios.health                # machine-readable health response and exit code
pytest runtime/tests -q
```

## Frozen integration contract

Member 2 owns the canonical TypeScript definitions in `packages/contracts`. Mirror them in
`runtime/src/helios/contracts/` with Pydantic. The JSON/HTTP wire format is Member 2's exact
camelCase spelling and every record includes `schemaVersion`. Python fields may remain snake_case
internally only if the shared base model uses Pydantic validation/serialization aliases,
`populate_by_name=True`, and every outbound dump uses aliases. Contract tests must compare serialized
JSON, not only Python objects.

### Task envelope received from the control plane

```json
{
  "schemaVersion": 1,
  "taskId": "task_01J...",
  "source": "github",
  "type": "triage",
  "repo": "owner/repo",
  "payload": {
    "event": "issues.opened",
    "issueNumber": 47,
    "title": "Checksum utility crashes on empty input",
    "body": "Reproduction details...",
    "authorLogin": "mentor",
    "htmlUrl": "https://github.com/owner/repo/issues/47",
    "baseSha": "0123456789abcdef"
  },
  "memoryPack": {
    "user": {},
    "issue": {},
    "repo": {}
  },
  "policyPack": {
    "version": "policy-sha",
    "rules": []
  },
  "lease": {
    "leaseId": "lease_01J...",
    "expiresAt": 1780000000000
  }
}
```

### Plan produced by the Planner

```json
{
  "schemaVersion": 1,
  "runId": "run_01J...",
  "taskId": "task_01J...",
  "lane": "fast",
  "plannerConfidence": 0.91,
  "nodes": [
    {
      "nodeId": "intake",
      "expert": "triage",
      "dependsOn": [],
      "inputArtifactRefs": [],
      "expectedArtifact": "classification",
      "acceptanceCriteria": ["triage.labels.allowed", "triage.priority.valid"],
      "budget": {
        "maxTokens": 600,
        "maxSeconds": 8,
        "tools": ["repo.read", "memory.read"]
      }
    }
  ]
}
```

### Artifact emitted by every expert

```json
{
  "schemaVersion": 1,
  "artifactId": "artifact_01J...",
  "runId": "run_01J...",
  "nodeId": "intake",
  "type": "classification",
  "producer": {"agent": "triage", "version": 1},
  "policyRuleIds": ["triage.priority.p2"],
  "content": {},
  "createdAt": 1780000000000
}
```

### Span event sent to Convex

```json
{
  "schemaVersion": 1,
  "eventId": "evt_01J...",
  "runId": "run_01J...",
  "spanId": "span_01J...",
  "parentSpanId": null,
  "nodeId": "intake",
  "agent": "triage",
  "agentVersion": 1,
  "model": "qwen3-4b-q4",
  "status": "completed",
  "startedAt": 1780000000000,
  "finishedAt": 1780000004300,
  "tokensIn": 420,
  "tokensOut": 91,
  "costUsd": 0,
  "costCloudEquivalentUsd": 0.00031,
  "latencyMs": 4300,
  "inputArtifactRefs": [],
  "outputArtifactRef": "artifact_01J...",
  "toolCalls": [],
  "verdict": null,
  "error": null
}
```

### Patch artifact for credential-free GitHub write-back

Member 2 will create the Git objects and branch through the GitHub REST API. You supply complete
tested file contents, not GitHub credentials.

```json
{
  "schemaVersion": 1,
  "type": "patch",
  "baseSha": "0123456789abcdef",
  "branchName": "hermes/task_01J-checksum-empty-input",
  "commitMessage": "fix: handle empty checksum input",
  "files": [
    {
      "path": "src/checksum.py",
      "mode": "100644",
      "encoding": "utf-8",
      "content": "complete post-change file content"
    }
  ],
  "tests": [
    {"command": "pytest -q", "exitCode": 0, "durationMs": 5120}
  ],
  "diffStat": {"files": 1, "additions": 6, "deletions": 1}
}
```

### Outbound control-plane HTTP endpoints supplied by Member 2

Your `ControlPlaneClient` calls these Convex HTTP actions with
`Authorization: Bearer $HELIOS_RUNTIME_TOKEN` and an `Idempotency-Key` header:

```text
POST /runtime/claim
POST /runtime/heartbeat
POST /runtime/run/start
POST /runtime/span
POST /runtime/artifact
POST /runtime/run/finish
POST /runtime/task/escalate
POST /runtime/writeback
GET  /runtime/control
```

Treat `409` as an idempotent replay or lost lease, `401/403` as a hard configuration failure,
`429/5xx` as retryable with bounded exponential backoff, and network loss as a reason to append
events to the local outbox for later replay.

When the local ladder is exhausted, POST to `$HELIOS_FALLBACK_URL` (Member 2's authenticated
Cloudflare Worker `/inference/fallback` route) with the same schema-constrained request used for a
local model, plus `runId`, `spanId`, `purpose`, token ceilings, and the attempted local-model
chain. Authenticate with `HELIOS_RUNTIME_TOKEN`. Member 2 returns provider/model, output, measured
tokens, latency, and actual USD cost. The remote-provider secret never enters this process. Record
that response as a normal model span with `execution_location: remote`; never relabel it as local or
`$0.000`.

### Local FastAPI surface you supply

The dashboard and desktop shell need a small, localhost-only runtime API for health, model
visibility, test flights, preflight checks, and rehearsal controls. This API is not the Convex
control-plane API above and must not become a second task database. Implement these endpoints:

```text
GET  /v1/health
  liveness only: process, version, uptime, instance ID

GET  /v1/ready
  readiness: workspace, control plane, model endpoints and poller state

GET  /v1/runtime/status
  queue/poller state, current run/node, pause observed, outbox depth and safe failure summary

GET  /v1/models
  configured models, endpoint health, loaded/pinned state, slots, RAM/VRAM and last transition

POST /v1/roles/test-flight
  validate an unactivated role draft and execute it against an approved canned task without
  granting GitHub write-back; return the normal run/span/artifact IDs

POST /v1/evals/run
  start the fast or full Gauntlet for an existing agent tag; return an eval-run ID

POST /v1/runtime/preflight
  run env, disk, git, llama.cpp, model, Convex and optional-provider checks without changing state

POST /v1/runtime/reload
  reload versioned agent definitions after Member 2 has activated an approved version; never
  mutate tools, policies or role definitions inside this endpoint
```

Bind to `127.0.0.1` by default. Use exact-origin CORS for the local dashboard, Tauri origin, and the
specific deployed Pages origin; never use `*`. All POST endpoints require `X-Helios-Token`, have
strict Pydantic request/response models, reject oversized bodies, and redact prompts, paths, issue
content, tokens and secrets from errors. GET endpoints return safe summaries only. Member 3 normally
creates tasks and activates roles through Convex; these local endpoints expose runtime capability,
not an alternate source of truth.

For the normal Role Builder path, handle Member 2's durable `role_test` tasks. A
`payload.stage = "persona_draft"` task uses the Planner to turn the plain-language job into a bounded
persona proposal, recommended brain card, minimal tool set and safe guardrails; emit a typed role
draft artifact without registering it. A `payload.stage = "test_flight"` task loads the exact draft
hash, runs only the approved canned task in a disposable workspace, forces dry-run/no-GitHub tools,
and emits objective pass/fail criteria plus normal spans/artifacts. The runtime never activates the
role; Member 2 performs activation only for the exact passing draft hash.

## Required environment variables

Send this list to Member 2 for `.env.example`. Secrets belong only in local `.env` files or the
appropriate hosted secret store.

```text
CONVEX_HTTP_URL=
HELIOS_RUNTIME_TOKEN=
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
HELIOS_WRITEBACK_MODE=dry-run
HELIOS_DEMO_MODE=1
LLAMA_PLANNER_URL=http://127.0.0.1:8081
LLAMA_TRIAGE_URL=http://127.0.0.1:8082
LLAMA_CODER_URL=http://127.0.0.1:8083
LLAMA_EMBED_URL=http://127.0.0.1:8084
HELIOS_FALLBACK_MODE=worker
HELIOS_FALLBACK_URL=http://127.0.0.1:8787/inference/fallback
LINKUP_API_KEY=
GIT_REPO_CACHE_ROOT=./workspace/repos
```

Never request `GITHUB_APP_PRIVATE_KEY`, `GITHUB_TOKEN`, `ELEVENLABS_API_KEY`, or Cloudflare
credentials. Those remain with Member 2.

## Exact implementation layout

Create the following modules. Keep files focused; avoid one giant runtime file.

```text
runtime/src/helios/
├─ __init__.py
├─ main.py                         # process lifecycle, poll loop, graceful shutdown
├─ health.py                       # hardware/model/control-plane health checks
├─ config.py                       # Pydantic settings and validation
├─ clock.py                        # injectable time for deterministic tests
├─ ids.py                          # ULID generation
├─ api/
│  ├─ app.py                       # FastAPI app and lifespan
│  ├─ auth.py                      # local token and exact-origin CORS
│  ├─ routes_health.py
│  ├─ routes_models.py
│  ├─ routes_roles.py
│  └─ routes_evals.py
├─ contracts/
│  ├─ task.py
│  ├─ plan.py
│  ├─ artifact.py
│  ├─ trace.py
│  ├─ agent.py
│  ├─ eval.py
│  └─ fixtures.py
├─ control_plane/
│  ├─ base.py                      # protocol/interface
│  ├─ convex_http.py               # real adapter
│  ├─ in_memory.py                 # independent development adapter
│  ├─ local_cache.py               # bounded claimed-task cache for network degradation
│  └─ outbox.py                    # offline event buffer and replay
├─ planning/
│  ├─ planner.py
│  ├─ prompts.py
│  ├─ grammar.py
│  ├─ validator.py
│  └─ fallback_templates.py
├─ scheduler/
│  ├─ dag.py
│  ├─ executor.py
│  ├─ budgets.py
│  ├─ retry.py
│  └─ resume.py
├─ models/
│  ├─ bootstrap.py
│  ├─ client.py
│  ├─ manager.py
│  ├─ registry.py
│  ├─ vram.py
│  └─ telemetry.py
├─ experts/
│  ├─ base.py
│  ├─ triage.py
│  ├─ dedupe.py
│  ├─ python.py
│  ├─ frontend.py
│  ├─ test.py
│  ├─ docs.py
│  ├─ debug.py
│  ├─ security.py
│  ├─ research.py
│  └─ critic.py
├─ agency/
│  ├─ registry.py
│  ├─ spawn.py
│  ├─ adjust.py
│  └─ escalation.py
├─ workspace/
│  ├─ artifacts.py
│  ├─ repository.py
│  ├─ worktrees.py
│  ├─ commands.py
│  └─ cleanup.py
├─ tools/
│  ├─ grants.py
│  ├─ repo_read.py
│  ├─ command_runner.py
│  ├─ github_read.py
│  └─ linkup_search.py
├─ lanes/
│  ├─ fast.py
│  └─ deep.py
├─ evals/
│  ├─ run.py
│  ├─ scorer.py
│  ├─ capture.py
│  └─ report.py
└─ demo/
   ├─ seed_runtime.py
   └─ fixtures.py
```

## Agent definitions

Create version-controlled definitions under `agents/`. Each file includes model, persona,
allowed tools, budgets, artifact output type, and whether critic approval is mandatory.

```text
agents/planner.yaml
agents/triage.yaml
agents/dedupe.yaml
agents/python.yaml
agents/frontend.yaml
agents/test.yaml
agents/docs.yaml
agents/debug.yaml
agents/security.yaml
agents/research.yaml
agents/critic.yaml
```

Use the model allocation promised in `soul.md`:

| Role | Default model | Runtime policy |
|---|---|---|
| Planner | Qwen3-8B Q4 | Pinned; thinking enabled only for deep tasks |
| Critic | Qwen3-8B Q4 | Same weights allowed, isolated context and persona |
| Triage/Docs/Security/Research | Qwen3-4B Q4 | Pinned or first eviction candidate after idle |
| Python/Frontend/Test/Debug | Qwen2.5-Coder-7B Q4 | Load on deep-lane demand |
| Dedupe | bge-small plus Qwen3-4B | Precomputed embeddings |

The critic model alone is not a correctness proof. Deterministic test output and policy checks
always override model confidence.

## Runtime behavior you must implement

### Claim, lease, heartbeat, and resume

1. Poll `/runtime/control`; do nothing when the whole crew or this instance is paused.
2. Claim one task from `/runtime/claim`.
3. Start a heartbeat coroutine at one-third of the lease duration.
4. Create `workspace/<task_id>/run-state.json` before inference begins.
5. Start a run and persist its identifier locally and remotely.
6. After every node, atomically write the artifact and completed-node list.
7. If the process restarts, resume from the last completed node instead of starting over.
8. If the lease is lost, stop all write-back attempts and mark the local run orphaned.

### Planner

The Planner receives only the normalized task, memory pack, policy pack, repo summary, expert
registry, and budgets. It emits schema-constrained JSON. Validate all of the following before
execution:

- Node identifiers are unique.
- Every dependency exists.
- The graph is acyclic.
- Every expert exists or a spawn node is explicitly requested.
- Every output artifact type is registered.
- Budgets are within global policy.
- Tool grants are a subset of the expert's allowed tools.
- At least one terminal critic node exists before write-back.
- Protected or security-sensitive work includes a security expert and escalation path.

Allow one schema-repair attempt. If it still fails, use a typed fallback plan and emit a
`planner_fallback` trace event; never hide the fallback.

### Scheduler

- Topologically execute the DAG.
- Run independent branches concurrently up to `HELIOS_MAX_PARALLEL_NODES`.
- Enforce token, time, and tool budgets before and during execution.
- Permit one revision retry when the critic returns concrete notes.
- Stop loops after two critic rejections and emit a `blocked` artifact.
- Cancel downstream work after a hard failure unless the plan marks the branch optional.
- Persist every transition: `queued`, `running`, `completed`, `revising`, `blocked`, `failed`.

### Typed artifact-only handoffs

Experts never rely on hidden chat history. Each receives only referenced artifacts and the
minimum policy/context needed for its job. Implement and test these artifact types:

```text
plan
classification
dup_report
research
repro_report
patch
test_result
security_report
review_notes
draft_reply
critic_verdict
blocked
escalation
release_draft
```

Every artifact must identify its producer, schema version, upstream references, policy rule
identifiers, and creation time.

### Fast lane

Implement the complete representative unit:

```text
new issue
→ planner
→ triage || dedupe || optional research
→ reply draft
→ critic
→ writeback intent: comment + labels + optional duplicate close
```

Keep the warmed target below 55 seconds. Record real latency even if the target is missed. Use
short grammar-constrained outputs and precomputed embeddings. The fast lane must produce a useful
reply, not merely a label.

### Complete task-type coverage

Do not stop after the two headline lanes. Preserve every maintainer duty promised in `soul.md` and
map it to a typed plan and write-back intent:

| Task type | Minimum plan and terminal artifact |
|---|---|
| `intake` / `classify` / `label` | triage → critic → classification plus labels, priority and optional milestone |
| `dedupe` | embedding candidates → dedupe expert → critic → linked duplicate notice and close intent only above policy threshold |
| `clarify` | missing-information checklist → reply draft → critic → specific reproduction-information request |
| `respond` | docs/code evidence plus optional Linkup → cited reply → critic → comment intent |
| `repro` | isolated worktree → deterministic reproduction command → `repro_report`; never claim reproduction from prose alone |
| `fix` | deep lane → tested patch → security → critic → branch/PR intent and policy-gated merge eligibility |
| `review` | inspect inbound PR diff/checks/policy → `review_notes` → critic → review-comment intent; never merge unless the separate hard gate passes |
| `docs` | docs expert → validation/link check → critic → docs-only patch/PR or autonomous merge eligibility |
| `release` | collect merged changes and links → release draft → critic → `release_draft`; publication is always forbidden |
| `escalate` | blocker plus entire artifact chain, attempted actions and next decision → escalation queue; never ask the human to restart analysis |

Unknown or unsupported task types must become a visible typed escalation, not a guessed write-back.
Fast and deep are latency/scheduling classes; they do not remove any of these product capabilities.

### Multi-repository isolation

Treat `repo` as a required isolation key, not a display label. Resolve the repository only through
the normalized allowlisted descriptor Member 2 supplies; use separate caches/worktrees, repo memory,
policy pack, embeddings, command configuration and artifact namespaces. Never use contributor facts,
CONTRIBUTING rules, duplicate candidates or source files from repository A while processing B.
Include `repo` in every local cache/outbox/dedupe key. Test the same issue number and same filename in
both demo repositories and prove their plans, policies and artifacts remain isolated.

### Deep lane

Implement:

```text
bug issue
→ plan
→ dedupe || reproduction
→ code expert
→ test expert
→ security expert
→ critic
→ patch artifact
→ Member 2 creates branch and PR
```

Create an isolated Git worktree per task. Commands run with a timeout, explicit working directory,
sanitized environment, output-size cap, and allowlist. Capture stdout, stderr, exit code, duration,
and command hash. Never run arbitrary commands copied directly from an issue.

### Dynamic expert spawning

Implement the exact L5 evidence path:

1. Planner determines no registered expert clears the capability threshold.
2. It calls `spawn_expert` with name, job, base weights, persona, minimal tools, and budget.
3. Validate that tool grants do not exceed policy.
4. Register the role through Member 2 with `origin: spawned` and `spawnedByRunId: runId`.
5. Emit `agent_spawned` before delegation.
6. Persist and reuse the expert on later matching tasks.

Keep a deterministic Rust issue fixture that spawns `rust-expert`; its tool permission must be
limited to repository reads/writes and `cargo` commands.

### Role self-adjustment

Track normalized critic failure classes across runs. When the same expert reaches its second
occurrence, create a persona-only constraint, register a new version, and emit the exact v1→v2 diff.
If the current node still has its single permitted revision attempt, use v2 for that attempt. If the
second rejection has already exhausted the run's retry limit, preserve v2 for the next matching task
and escalate the current run—never take an invisible third attempt. Never overwrite the old
definition. Policy/tool/guardrail changes require human approval; only a bounded prompt constraint
may self-adjust automatically.

### Research Expert and Linkup

Use Linkup only when live information can change the answer: upstream issues, dependency release
notes, error strings, or current advisories. Store query, result title, URL, excerpt, retrieval time,
and which claim used it. Draft replies must cite the original URL. If Linkup fails, continue without
research when optional or escalate when the plan marked it required.

### Critic

Return exactly one verdict:

```text
pass     → produce signed write-back intent
revise   → concrete criterion-level notes and target node
blocked  → escalation artifact with exact blocker
```

The critic checks the plan's acceptance criteria, policy rule IDs, artifact schema, factual support,
test results, patch size, protected paths, and reply tone. It may never convert a failed command into
a pass based on prose reasoning. Triage emits an explicit sentiment/risk flag; angry or abusive-user
contexts and any draft containing disallowed profanity, harassment, secrets, or unsupported security
claims become a typed escalation instead of an autonomous reply.

### Local model manager and telemetry

- Discover RAM, GPU, VRAM and llama.cpp availability at startup.
- Pin the planner, triage and embedding models when hardware allows.
- Maintain an LRU list for cold coder experts.
- Emit `model_load_started`, `model_loaded`, `model_evicted`, `model_request`, and
  `model_request_completed` events.
- Sample VRAM/RAM/CPU every second during a run.
- Include cold-start time separately from generation latency.
- Implement the promised planner fallback ladder in this order: local Qwen3-8B, local Qwen3-4B,
  Member 2's Workers AI provider, then Member 2's configured Haiku-compatible provider. Stop at the
  first valid schema-constrained result and emit one attempt event for every failed rung.
- Use `$HELIOS_FALLBACK_URL` for hosted providers so their credentials remain server-side.
  If all remote providers are disabled, fail visibly or use the declared typed fast-lane template;
  never silently substitute a different service.
- Never claim `$0.000` for a remote fallback; record the actual configured cost.

## Evaluation ownership

You own the Gauntlet cases and evaluation executable. Member 2 owns CI invocation and persistence;
Member 3 owns visualization.

Create at least 40 cases:

- 25 triage cases with exact classification, label, priority, and duplicate expectations.
- 8 response cases with hard assertions and a held-out critic rubric.
- 7 fix cases with frozen repository fixtures and objective tests.

Each case contains:

```text
case.yaml             # id, kind, input, golden, scorer, timeout, tags
repo/ or repo_ref     # frozen code input for fix cases
expected/             # expected labels, strings, test results, or patch properties
```

`python -m helios.evals.run` must output JSON plus a human-readable summary and use nonzero exit
status below thresholds. `--ci` enforces at least 85% overall, 85% triage, 85% response and 70% fix;
the final `agents-v4` evidence requires three consecutive complete Gauntlet runs at at least 85%
overall with no case-set or version change between runs. Support version tags `agents-v1` through
`agents-v4`. Capture failed, escalated, or human-corrected work as `pending-review` eval candidates
through Member 2's endpoint.

## Hour-by-hour execution plan

### Hours 0–2 — Contracts and independent skeleton

- Agree on IDs, timestamps, task states, artifact names, and endpoint paths with Members 2 and 3.
- Create the Python package, config, health command, Pydantic contracts, and in-memory adapter.
- Start the localhost FastAPI surface on port 8788 with fake health/model/test-flight responses.
- Provide Member 2 with required environment variables and fixture payloads.
- Provide Member 3 with one complete seeded run containing a parallel DAG and critic revision.
- Make `pytest runtime/tests/contracts -q` pass before changing runtime behavior.

**Handoff at hour 2:** contract fixture JSON, health output schema, and fake trace bundle.

### Hours 2–6 — Vertical slice with deterministic fake models

- Implement claim/heartbeat/start/span/artifact/finish through the in-memory adapter.
- Implement planner validation, DAG execution, typed artifacts, and critic routing.
- Use deterministic fake model outputs first.
- Complete `issue → plan → triage → critic → writeback intent` locally.
- Confirm Member 3 can render your fixture and Member 2 accepts your HTTP payloads.

**Exit test:** one command produces a complete run folder and valid write-back intent without
Convex, GitHub, or llama.cpp.

### Hours 6–10 — Real fast lane

- Wire llama.cpp clients and model manager.
- Add schema-constrained planner, triage, reply, and critic calls.
- Add bge-small dedupe and optional Linkup research.
- Integrate Member 2's real claim/trace/artifact endpoints.
- Tune outputs and contexts against ten fast-lane fixtures.
- Record honest warm and cold latency.

**Handoff at hour 10:** real completed run visible in Convex and Member 3's trace page.

### Hours 10–16 — Deep lane and worktrees

- Implement repository cache, task worktrees, safe command runner, reproduction, patch, tests, and
  security report.
- Produce the credential-free patch artifact expected by Member 2.
- Test branch/PR creation with Member 2 against the demo repository.
- Add crash resume and local event outbox.
- Add a bounded redacted local cache with restrictive file permissions for tasks already claimed
  while online. During a
  Convex outage, continue only when the stored lease remains valid or in explicitly labelled dry-run
  mode; buffer events and revalidate the lease before any later write-back. Never pull invented work
  from fixtures into live mode.

**Exit test:** a real bug fixture becomes a green PR through the full merged path.

### Hours 16–21 — Emergent organization features

- Implement `spawn_expert`, the deterministic Rust spawn fixture, and registry persistence.
- Implement blocked artifacts, replan-or-escalate behavior, and context-complete escalation.
- Implement persona-only role self-adjustment with version diff.
- Save one critic `revise → improved artifact → pass` run.

**Handoff at hour 21:** bookmarked run IDs for spawn, revision, and escalation UI evidence.

### Hours 21–27 — Gauntlet, memory, policies, and telemetry

- Expand to 40 eval cases and implement scorers.
- Verify the Planner receives and cites all three memory layers supplied by Member 2.
- Implement policy rule citation and protected-path preflight checks.
- Finish model load/eviction/VRAM timeline events.
- Integrate captured-failure eval creation.

**Exit test:** full Gauntlet JSON report, version metadata, and threshold exit code.

### Hours 27–31 — Performance and reliability

- Run ten consecutive warmed fast-lane tasks.
- Remove unnecessary context and output tokens without weakening content.
- Test lease loss, Convex outage, model timeout, malformed JSON, command timeout, failed tests,
  critic loops, and process restart.
- Verify the outbox replays once and never duplicates spans/artifacts.
- Verify degraded cached-task execution never writes after lease expiry and is visibly marked
  offline/degraded in every buffered span.
- Exercise local and remote inference fallback paths.
- Test every local FastAPI route, local-token rule, exact-origin CORS rule, and response redaction.

### Hours 31–34 — Integration freeze

- Merge from `integration`, run all contract and runtime tests, and resolve only runtime-owned bugs.
- Produce seed data for every dashboard screen.
- Freeze `agents-v4`; do not tune prompts after the final three Gauntlet runs unless fixing a hard
  failure and rerunning all evidence.
- Give Member 3 exact run IDs and GitHub URLs for the demo.

### Hours 34–36 — Rehearsal and standby

- Keep all model servers warm.
- Run the demo sequence twice from a clean process start.
- Record a fallback trace bundle and verify it can be replayed without inference.
- During judging, watch runtime logs, leases, VRAM, and escalation state; do not touch the UI or
  GitHub manually unless the documented emergency procedure is invoked.

## Required tests

Create automated tests for all of these before declaring your lane complete:

### Contracts and planner

- Every shared JSON fixture validates in TypeScript and Pydantic.
- Unknown schema versions fail clearly.
- Cycles, missing dependencies, excessive budgets, unknown tools, and absent critic nodes fail.
- One malformed plan is repaired; a second failure selects a visible fallback plan.

### Scheduler and handoffs

- Parallel nodes actually overlap in time.
- Downstream nodes receive artifact references rather than hidden chat history.
- Token/time/tool budgets terminate work.
- One revision retry succeeds; two equivalent rejections escalate.
- Restart resumes from the last completed node.
- Network loss permits only valid-leased cached work or dry-run work; write-back waits for lease
  revalidation and outbox replay stays idempotent.

### Safety

- Commands outside the allowlist are rejected.
- Worktree paths cannot escape `HELIOS_WORKSPACE_ROOT`.
- Failed tests can never generate a passing critic verdict.
- Protected path changes generate escalation.
- Two repositories with colliding issue numbers/paths cannot share memory, artifacts, embeddings,
  worktrees or write-back intents.
- GitHub and Cloudflare secrets never appear in prompts, artifacts, traces, or logs.

### Models and agents

- Model cold load, warm reuse, eviction, and fallback all emit telemetry.
- Spawned expert has `origin: spawned` and the correct birth run.
- Role adjustment creates version 2 without mutating version 1.
- Linkup citations retain URL and retrieval time.
- Angry-user sentiment and unsafe draft-content fixtures escalate with the full draft/context and
  never produce a write-back intent.
- The fallback ladder records every attempted rung and the returned hosted cost/provider honestly.

### Local API and task coverage

- Health/readiness/model GET routes expose safe typed data and no secret-bearing configuration.
- Every POST rejects missing/invalid `X-Helios-Token`; unapproved origins receive no CORS access.
- Role test flight cannot write to GitHub or activate its own role.
- Intake, clarify, respond, repro, fix, inbound review, docs and release-draft fixtures each produce
  their declared artifact and write-back intent or a context-complete escalation.

### Lanes and evaluation

- Fast lane produces classification, dedupe result, substantive reply, critic verdict, and
  write-back intent.
- Deep lane creates a patch that fails before the change and passes afterward.
- Full Gauntlet has at least 40 cases and repeatable scoring.
- Ten warmed fast-lane runs have recorded latency and actual cost, even if a target is missed.

## Member 1 definition of done

- `python -m helios.health` reports healthy models, workspace, and control-plane connectivity.
- FastAPI on `127.0.0.1:8788` supplies all documented health, model, preflight, eval and test-flight
  routes with authentication/CORS tests.
- The runtime operates against both in-memory and real Convex adapters.
- Fast and deep lanes complete end to end.
- Every maintainer task type in `soul.md` has a tested typed plan; releases remain draft-only.
- Every step produces a searchable span and typed artifact.
- Dynamic spawn, blocked escalation, critic revision, and role adjustment are reproducible.
- Linkup research creates cited artifacts.
- Three memory layers and policy rule IDs influence and appear in plans.
- Model load/eviction and VRAM telemetry are visible to Member 3.
- The 40-case Gauntlet runs locally and under Member 2's CI command.
- No GitHub credential exists anywhere in your files or process.
- Member 2 can turn your write-back intent into real GitHub output.
- Member 3 can render every required view using your live events and saved runs.

## Merge and handoff checklist

1. Work on `member1/runtime`; never force-push after another member consumes a commit.
2. Rebase on `integration` at the hour-10, hour-21, and hour-31 checkpoints.
3. Before requesting a merge, run:

   ```bash
   pytest runtime/tests -q
   python -m helios.evals.run --fast
   python -m helios.health
   ```

4. Include fixture updates with every contract-affecting change.
5. State which Member 2 endpoint and Member 3 screen each new event/artifact supports.
6. Do not edit another member's path to make your tests pass; open a precise integration request.
7. After merge, run `pnpm dev` from the root and complete one live fast task plus one deep task.
8. Tag the final agent set only after three complete Gauntlet runs and Member 3 has captured the
   corresponding dashboard evidence.
