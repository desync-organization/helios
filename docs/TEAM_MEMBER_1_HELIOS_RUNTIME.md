# Team Member 1 — Helios Runtime and Agent Execution

## Mission

Own the on-device Helios execution plane. Turn a claimed Hermes maintainer task into a bounded,
traceable plan; execute specialist work through typed artifacts; obtain an independent critic verdict;
and return a credential-free write-back intent to Member 2.

Your lane proves that Hermes is an agency rather than a scripted interface: plans differ by task,
independent branches run in parallel, specialists can be spawned, blocked work escalates with full
context, and every model/tool action is observable and resumable.

## Planning baseline — 12 July 2026

- The existing root Next.js frontend in `src/` and `public/` is accepted as complete and frozen for
  this work split. Do not scaffold another dashboard, add routes/components, redesign it, or move it
  into an `apps/dashboard` package.
- The repository uses the current root Next.js/Bun setup. Do not introduce the obsolete Vite/pnpm
  monorepo assumed by the earlier plan.
- “Frontend Expert” in `soul.md` is still a required **agent role that fixes TypeScript/React code in
  maintained repositories**. It is not an assignment to build the Hermes frontend. In code and new
  prose, call it `web-typescript` where that avoids confusion.
- `soul.md` remains the product source of truth for the Hermes/Helios identity, maintainer task types,
  typed handoffs, independent critic, guardrails, real GitHub output, latency, and evidence.
- Frontend construction is not hidden inside “integration.” Your responsibility stops at canonical
  backend events and stable service interfaces. Member 3 owns the compatibility gateway and end-to-end
  verification against the already-built client.

## Multipurpose operating model

Helios must not contain three unrelated hard-coded pipelines. Implement one planner/scheduler/artifact
kernel with mode-specific expert packs, policy packs and acceptance criteria.

### Mode A — GitHub maintainer (`maintain`)

This is the primary `soul.md` job and judged vertical slice. It reacts to GitHub issues, comments, PRs
and releases; classifies and deduplicates work; answers questions; reproduces and fixes bugs; reviews
changes; updates documentation; drafts releases; and escalates exceptional work with full context.

### Mode B — Product builder (`build`)

This mode accepts a product brief or repository-scoped feature request and produces:

```text
requirements_spec
→ architecture_decision
→ implementation_plan/DAG
→ parallel web/backend/test/docs/security work
→ integrated build
→ test/security/critic gates
→ branch-and-PR intent plus build manifest
```

Builder mode is not allowed to create or deploy arbitrary infrastructure merely because a prompt asks.
Repository creation, deployment, paid-provider use, production credentials, destructive migrations and
live environment changes require explicit policy and a human confirmation through Member 2.

### Mode C — Repository security auditor (`security_audit`)

This mode is defensive, scoped and read-only by default:

```text
scope/consent
→ repository inventory
→ dependency ∥ secret ∥ SAST ∥ config/workflow analysis
→ normalize/dedupe findings
→ evidence/reachability/severity review
→ independent critic
→ private report
→ optional separately approved remediation patch + tests + rescan
```

Never scan an external host, execute an exploit, exfiltrate a secret, publish an unpatched finding, or
turn a read-only audit into a mutation. The Security Expert can reason about evidence and remediation;
deterministic scanners, repository state and policy remain authoritative.

### Shared invariants across all modes

- Every task is tied to an allowlisted repository, explicit mode, policy version and consent scope.
- Planner output is a typed per-request DAG, not a route-table shortcut.
- Experts communicate only through typed artifacts.
- Tool access is minimal, declared per node and enforced outside the model.
- Every external effect is an intent until Member 2's independent policy/write-back checks pass.
- Every artifact can be searched, replayed, evaluated and traced to model/prompt/adapter/tool versions.
- A fixture, dry-run or generated preview never counts as a real GitHub completion.
- Security and privacy rules cannot be relaxed by Planner, Critic, role adjustment or LoRA.

## Equal three-person split

All three members receive the same 36-hour schedule: approximately 30 hours of owned engineering and
6 hours of shared integration, evidence, and rehearsal.

| Member | Primary lane | Not their lane |
|---|---|---|
| **1 — Runtime** | Planner, scheduler, experts, models, tools, workspace, critic, runtime safety | Frontend, cloud persistence, model training/eval ownership |
| **2 — Control plane** | Contracts, Convex, Cloudflare, GitHub App/write-back, policy, memory, external integrations | Frontend, local orchestration internals, training/scoring |
| **3 — Model quality** | LoRA/QLoRA, datasets, Gauntlet, realtime compatibility gateway, reliability, evidence | Frontend construction, credentialed GitHub mutations, scheduler internals |

No member should absorb another lane merely because a fixture is temporarily available. Build against
the agreed boundary, file an integration issue, and continue with the local fake.

## Repository ownership

You own:

```text
runtime/
  pyproject.toml
  src/helios/
  tests/
  fixtures/
agents/                         # baseline personas, tools, budgets, adapter selection
workspace/README.md             # workspace contract only; live contents stay ignored
```

You do not own:

```text
src/ and public/                # completed frontend; frozen
convex/, apps/worker/           # Member 2
packages/contracts/, policy/    # Member 2
training/, datasets/, evals/    # Member 3
adapters/, benchmarks/          # Member 3
gateway/, tests/e2e/, evidence/ # Member 3
.github/, package.json          # Member 2 integration ownership
```

Member 2 owns canonical TypeScript/wire contracts. You own their Pydantic mirror. Member 3 owns
adapter/eval schemas, but any record crossing a service boundary must also be represented in Member
2's canonical contract package.

## Required runtime commands

Implement and keep stable:

```bash
python -m helios.main
python -m helios.health
python -m helios.models.bootstrap
python -m helios.demo.seed_runtime
pytest runtime/tests -q
```

`python -m helios.evals.run` may remain as a thin compatibility shim, but it must call Member 3's
versioned evaluator. Do not duplicate cases or scoring logic inside `runtime/`.

Use Python 3.12+, FastAPI, Pydantic, HTTPX, asyncio, psutil and YAML parsing. Treat llama.cpp and model
files as explicit external prerequisites checked by bootstrap.

## Implementation layout

Keep modules small and mode-neutral where possible:

```text
runtime/src/helios/
├─ main.py
├─ config.py
├─ health.py
├─ ids.py
├─ clock.py
├─ api/
│  ├─ app.py
│  ├─ auth.py
│  ├─ health.py
│  ├─ models.py
│  ├─ roles.py
│  └─ evals.py                 # thin shim into Member 3's evaluator
├─ contracts/
│  ├─ task.py
│  ├─ plan.py
│  ├─ artifact.py
│  ├─ trace.py
│  ├─ security.py
│  ├─ build.py
│  └─ adapter.py
├─ control_plane/
│  ├─ base.py
│  ├─ convex_http.py
│  ├─ in_memory.py
│  ├─ local_cache.py
│  └─ outbox.py
├─ planning/
│  ├─ planner.py
│  ├─ grammar.py
│  ├─ validator.py
│  ├─ context.py
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
│  ├─ adapters.py
│  ├─ vram.py
│  └─ telemetry.py
├─ experts/
│  ├─ triage.py
│  ├─ dedupe.py
│  ├─ web_typescript.py
│  ├─ backend.py
│  ├─ test.py
│  ├─ docs.py
│  ├─ debug.py
│  ├─ security.py
│  ├─ research.py
│  └─ critic.py
├─ modes/
│  ├─ maintain.py
│  ├─ build.py
│  └─ security_audit.py
├─ security/
│  ├─ inventory.py
│  ├─ scanner_runner.py
│  ├─ normalize.py
│  ├─ findings.py
│  ├─ redaction.py
│  └─ remediation.py
├─ workspace/
│  ├─ artifacts.py
│  ├─ repositories.py
│  ├─ worktrees.py
│  ├─ commands.py
│  └─ cleanup.py
├─ tools/
│  ├─ grants.py
│  ├─ repo_read.py
│  ├─ command_runner.py
│  ├─ scanner.py
│  └─ research.py
├─ agency/
│  ├─ registry.py
│  ├─ spawn.py
│  ├─ adjust.py
│  └─ escalation.py
└─ demo/
   ├─ seed_runtime.py
   └─ fixtures.py
```

Mode modules assemble plans and expert packs; they must not duplicate scheduler, model, workspace,
artifact or policy enforcement.

## Required configuration

Ask Member 2 to document these non-secret runtime variables in `.env.example`:

```text
CONVEX_HTTP_URL=
HELIOS_RUNTIME_TOKEN=
HELIOS_INSTANCE_ID=demo-laptop-1
HELIOS_API_HOST=127.0.0.1
HELIOS_API_PORT=8788
HELIOS_LOCAL_API_TOKEN=
HELIOS_WORKSPACE_ROOT=./workspace
HELIOS_OUTBOX_PATH=./workspace/outbox.jsonl
HELIOS_MAX_VRAM_MB=7600
HELIOS_MAX_PARALLEL_NODES=3
HELIOS_FAST_LANE_TIMEOUT_S=55
HELIOS_DEEP_LANE_TIMEOUT_S=480
HELIOS_SECURITY_SCAN_TIMEOUT_S=600
HELIOS_WRITEBACK_MODE=dry-run
HELIOS_DEFAULT_MODE=maintain
LLAMA_PLANNER_URL=http://127.0.0.1:8081
LLAMA_TRIAGE_URL=http://127.0.0.1:8082
LLAMA_CODER_URL=http://127.0.0.1:8083
LLAMA_EMBED_URL=http://127.0.0.1:8084
HELIOS_FALLBACK_URL=http://127.0.0.1:8787/inference/fallback
HELIOS_ADAPTER_MANIFEST=./adapters/promoted/active.json
GIT_REPO_CACHE_ROOT=./workspace/repos
```

Do not request GitHub, Cloudflare, Linkup, vulnerability-provider or voice credentials. External
providers must be proxied by Member 2 under consent/data-egress policy.

## Frozen service boundaries

### Control plane supplied by Member 2

Use authenticated, schema-versioned, idempotent endpoints for:

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

Treat `401/403` as hard configuration failures, a lost-lease `409` as an immediate stop to live
write-back, `422` as a contract bug, and `429/5xx` as bounded-retry conditions. Buffer trace events in
a local outbox and replay them idempotently; never continue a live mutation after lease expiry.

### Canonical events consumed by Member 3

Emit typed events; do not format UI prose. Every event must include at least:

```text
schemaVersion, eventId, type, source, timestamp, sequence,
taskId?, runId?, spanId?, payload, redactionLevel
```

Events cover task/run transitions, agent status, plan nodes, artifacts, critic verdicts, model
load/eviction, token/cost/latency, tool calls, fallback use, escalation, and terminal result URLs.
Member 3 maps these records to the frozen client's WebSocket messages.

### Adapter package supplied by Member 3

Member 3 supplies a promoted adapter package and manifest. You validate before loading:

```text
adapterId, adapterVersion, adapterSha256, format,
baseModelId, baseModelRevision, baseModelSha256, tokenizerSha256,
targetRoles[], trainingRunId, datasetManifestSha256,
lora{rank, alpha, dropout, targetModules}, quantization,
evalReportSha256, promotedAt
```

A hash or base-model mismatch is a visible readiness failure. Never guess compatibility.

## Primary deliverables

### 1. Runtime process, health, and independent development adapter

- Start the poller, scheduler, local API, model manager and outbox with graceful shutdown.
- Provide an in-memory control-plane adapter so runtime work never waits for Convex.
- Bind local APIs to `127.0.0.1` by default; require a local token for mutations and exact-origin CORS.
- Expose liveness, readiness, runtime state, model state, preflight and safe reload endpoints.
- Redact secrets, raw private issue bodies, local paths and tokens from errors and logs.

### 2. Planner and scheduler

The Planner sees only the normalized task, bounded memory pack, policy pack, repository summary,
available expert registry and budgets. It emits schema-constrained JSON and never writes to GitHub.

Validate before execution:

- unique node IDs, existing dependencies and an acyclic graph;
- registered expert or explicit spawn request;
- known artifact type and valid acceptance criteria;
- budget and tool grants within policy;
- terminal independent critic before any write-back;
- security expert and escalation path for sensitive work.

Allow one schema-repair attempt. A second failure selects a typed fallback plan and emits an honest
`planner_fallback` event. The scheduler topologically executes the DAG, overlaps independent nodes,
enforces token/time/tool limits, permits one critic-directed revision, and blocks after two rejections.

### 3. Typed artifact-only handoffs

Implement versioned artifacts for:

```text
plan, classification, dup_report, research, repro_report, patch,
test_result, security_report, review_notes, draft_reply,
critic_verdict, blocked, escalation, release_draft,
requirements_spec, architecture_decision, implementation_plan,
build_manifest, package_result, deployment_draft,
repository_inventory, dependency_inventory, sbom,
secret_finding, vulnerability_finding, threat_model,
remediation_plan, sarif_report
```

Every artifact identifies its producer/version, upstream references, policy IDs, content hash and
creation time. Experts receive referenced artifacts—not hidden chat history. A human escalation must
contain `whatI tried`, exact failure, smallest failing case, artifact chain, and the decision needed.

### 4. Complete maintainer task coverage

Implement typed plans and terminal intents for every task declared in `soul.md`:

| Task | Minimum safe outcome |
|---|---|
| intake/classify/label | Classification, allowed labels, priority and optional milestone |
| dedupe | Candidate evidence, critic-approved linked notice, threshold-gated close intent |
| clarify/respond | Specific request or evidence-backed reply with source links |
| repro | Isolated deterministic reproduction report; never claim success from prose |
| fix | Tested patch, security report, critic verdict and branch/PR intent |
| review | Evidence-backed review notes; merge eligibility remains a separate hard gate |
| docs | Validated docs patch and docs-only merge eligibility |
| release | Draft release only; publication is forbidden |
| escalate | Complete context and a precise human decision request |

The fast lane is `planner → triage ∥ dedupe ∥ optional research → reply → critic → intent` and targets
55 seconds warmed. The deep lane uses an isolated worktree, safe command runner, code expert, tests,
security expert and critic before returning a complete-file patch artifact.

### 5. Product-builder execution

Builder mode must handle both a feature inside an existing repository and a bounded new-project brief.
For the hackathon, prefer an existing or pre-approved destination repository so GitHub permissions,
branch policy and CI are real.

#### Requirements stage

- Convert the operator request into goals, non-goals, user stories, constraints, acceptance criteria and
  unanswered decisions.
- Cite repository files, package versions and existing conventions used to infer constraints.
- Do not invent authentication, payment, deployment, data retention or privacy decisions. Emit a
  decision-required blocker when those materially change the product.
- Make requirements a versioned artifact the later critic can check.

#### Architecture stage

- Inspect the repository before choosing a stack or folder layout.
- Prefer existing frameworks and patterns over gratuitous replacement.
- Record alternatives, chosen approach, affected modules, data flow, migration impact, test plan,
  security considerations and rollback.
- Split the implementation into independently testable nodes with explicit file/artifact dependencies.

#### Implementation stage

- Delegate web/TypeScript, backend, data, test, docs and security nodes only when the task needs them.
- Parallel branches must not edit the same file without an integration node that resolves ownership.
- Agents emit complete file contents or a structured patch against the recorded base SHA.
- Stream code artifacts and progress as canonical events for Member 3's gateway; never let gateway/UI
  state replace workspace artifacts.
- Run formatter/typecheck/compiler/unit/integration commands already declared by the repository.

#### Integration and delivery stage

- Apply outputs to one isolated worktree in dependency order.
- Run the complete relevant test/build suite, not just each specialist's narrow test.
- Run the security pack before the Critic.
- Produce a build manifest listing files, commands, test results, known limitations and result hashes.
- Return a branch/PR intent by default. Deployment remains a draft/plan unless Member 2 policy includes
  explicit target, confirmation and credentials.

Builder acceptance scenarios:

1. add a small API plus tests to an existing repository;
2. add a TypeScript component plus backend contract without breaking the build;
3. create a bounded small project in an approved empty repository;
4. handle a missing product decision through a context-complete escalation;
5. reject a request for secrets or production deployment without consent.

### 6. Repository security-audit execution

Security mode must be useful to a maintainer and safe enough to run on a real repository.

#### Scope and inventory

- Verify `securityAuditOptIn`, repository/commit identity, visibility, allowed scanners, network policy,
  paths/exclusions, maximum runtime and whether remediation is permitted.
- Inventory languages, manifests, lockfiles, build tools, workflows, container/IaC files, entry points,
  authentication boundaries and exposed configuration.
- Produce a repository inventory before launching scanners; unsupported ecosystems become an explicit
  coverage limitation, not a clean bill of health.

#### Deterministic scanner layer

- Execute only configured local commands through the sandboxed runner.
- Record scanner name/version, rule database version, command hash, config, exclusions, start/end,
  exit code and truncated/redacted output reference.
- Dependency analysis must use the committed lockfile where present.
- Secret scanning must redact values immediately and persist only fingerprints/location/type.
- SAST/config findings must include exact rule/evidence locations and avoid claiming runtime
  exploitability without proof.
- Generate normalized findings and an SBOM/SARIF-style artifact where the selected tools support it.

#### Expert analysis layer

- Deduplicate scanner results by stable fingerprint and common root cause.
- Separate severity from confidence, exploitability and reachability.
- Use primary advisory sources through Member 2's proxy for CVE/CWE claims; preserve URL/retrieval time.
- The model may explain or recommend; it may not fabricate scanner success, a CVE, package version or
  proof of exploitability.
- Any discovered credential is treated as compromised: redact, recommend rotation and escalate.

#### Remediation layer

- A read-only audit ends with a private report intent and no repository mutation.
- Remediation requires a separately authorized task or explicit permission in the original consent.
- Prefer minimal dependency upgrades/config changes/code fixes with targeted regression tests.
- Re-run the relevant scanner and full impacted test suite after patching.
- Return a security PR intent with before/after findings and residual risk. Advisory publication is
  always human-controlled.

Security acceptance scenarios:

1. vulnerable dependency found from a lockfile, linked to authoritative advisory evidence, fixed and
   rescanned;
2. fake-secret fixture found while the raw value never enters artifact/trace/event output;
3. deliberate SAST false positive marked with a reproducible reason;
4. high-severity finding escalated privately rather than posted to a public issue;
5. external target/exploit request rejected before any command runs;
6. read-only audit verified to make zero GitHub mutations.

### 7. Workspace, tools, and deterministic safety

- Use one isolated worktree/cache/artifact namespace per repository and task.
- Sanitize command environments; enforce working directory, command allowlist, timeout and output cap.
- Never execute arbitrary commands copied from an issue.
- Keep repository A's files, policies, memory, embeddings and contributor facts out of repository B.
- A failed command/test can never be turned into a passing result by model confidence.
- No runtime process receives GitHub App private keys, installation tokens, Cloudflare keys or
  ElevenLabs credentials.

### 8. Models, experts, and LoRA runtime integration

Use the model allocation in `soul.md`: Qwen3-8B for Planner/Critic, Qwen3-4B for high-volume text
experts, Qwen2.5-Coder-7B for code experts, and bge-small for dedupe. Pin the hot set when hardware
allows and LRU-evict cold experts.

For adapters:

- Load Member 3's GGUF LoRA adapter separately from its exact GGUF base using llama.cpp.
- Select adapters by versioned agent definition, not by task text or an untrusted payload.
- Emit `baseModel`, base quantization, `adapterId/version/hash`, scale and training run on every model
  span.
- Support an explicit base-model fallback and one-command adapter rollback.
- Keep Planner base-first. Keep Critic on an independent base/persona and never attach the adapter that
  produced the artifact it judges.
- LoRA may improve classification, formatting or maintainer voice; it must never grant tools, weaken
  policy, encode secrets, or replace live repository memory/RAG.

Member 3 trains and promotes adapters. You provide a deterministic adapter smoke test and the runtime
loader; do not start an unreviewed online self-training loop.

### 9. Emergent organization and reliability

- Spawn an expert only when no registered capability clears the threshold; validate minimal tools and
  budget, persist `origin: spawned`, and emit the birth event before delegation.
- Keep the deterministic Rust fixture that creates `rust-expert` mid-run.
- Allow only bounded persona constraints to self-adjust after repeated normalized critic failures.
  Tool, model, adapter, policy and guardrail changes always require promotion/approval.
- Resume after restart from the last completed node.
- On network loss, continue only already-claimed work with a still-valid lease or explicit dry-run.
- Revalidate the lease before write-back and mark degraded/offline spans honestly.
- Implement the declared local 8B → local 4B → Member 2 hosted fallback ladder with actual cost.

## 36-hour execution plan

| Hours | Owned outcome |
|---|---|
| 0–4 | Python skeleton, Pydantic mirror, in-memory adapter, health/preflight, canonical event fixtures |
| 4–10 | Planner validation, DAG scheduler, artifacts, critic loop, deterministic fast slice, real llama.cpp fast lane |
| 10–18 | Maintainer deep lane, worktrees/safe commands, complete maintainer task types, credential-free patch intent |
| 18–26 | Builder requirements→PR lane, security inventory/scanner/finding/remediation lane, spawn/escalation and mode-specific experts |
| 26–30 | Resume/outbox, model manager/adapter loader, telemetry, ten fast runs, multi-repo/security/fallback hardening |
| 30–34 | Shared integration: all three modes through Member 2, Member 3 adapter/gateway/evaluator, fix runtime-owned blockers |
| 34–36 | Two rehearsals, model warm-up, frozen runtime configuration and live operations standby |

## Mandatory tests

### Contracts and scheduling

- Shared JSON fixtures round-trip exactly between TypeScript and Pydantic.
- Unknown schema versions, cycles, missing dependencies, excessive budgets and absent critics fail.
- Parallel nodes overlap in measured time; token/time/tool budgets terminate work.
- One critic revision can pass; two equivalent rejections escalate with context.
- Restart resumes without duplicating completed spans or artifacts.

### Safety and isolation

- Command and path traversal attempts are rejected.
- Failed tests, protected paths and unsafe content cannot generate live write-back intents.
- Colliding issue numbers/paths across two repositories remain isolated.
- Lease loss cancels write-back; outbox replay is idempotent.
- No server or provider secret appears in prompt, artifact, trace, log or event projection.

### Models and adapters

- Cold load, warm reuse, eviction and every fallback rung emit honest telemetry.
- Base/adapter mismatch fails readiness; promoted adapter loads by exact hash.
- Adapter-off rollback restores baseline behavior without changing the base model.
- Producer-adapter configuration never leaks into Critic configuration.
- Member 3's same held-out case can run base and adapter paths deterministically.

### Product lanes

- Fast lane produces classification, dedupe result, useful reply, critic verdict and intent.
- Deep lane creates a patch whose reproduction fails before and passes after the fix.
- Every maintainer task type produces its declared artifact/intent or a complete escalation.
- Builder mode produces requirements, architecture, integrated files, full build/test/security evidence,
  manifest and a single branch/PR intent.
- Builder specialists with overlapping files are serialized through an integration node.
- Security read-only mode produces normalized redacted findings and makes zero mutations.
- Security remediation produces a minimal tested patch, rescan delta and private PR intent.
- Secret fixtures never reveal their raw values in prompts, artifacts, events, traces or reports.
- Unauthorized exploit/external-scan requests are rejected before tool execution.
- Ten warmed fast runs record latency and actual cost even when a target is missed.

## Definition of done

- Runtime works against both in-memory and real Member 2 control-plane adapters.
- Fast/deep lanes and all `soul.md` maintainer task types are tested.
- The same runtime completes a product-build brief and a defensive repository audit without a separate
  hard-coded orchestrator.
- Builder output compiles/tests and arrives as a policy-gated PR intent.
- Security output is reproducible, redacted, evidence-backed and read-only unless remediation is
  separately authorized.
- Every step emits canonical searchable spans/artifacts and realtime events.
- Dynamic plans, critic revision, spawn, self-adjustment and escalation are reproducible.
- Three memory layers and policy IDs visibly affect plans.
- LoRA adapter loading is hash-checked, traced, benchmarkable, optional and instantly reversible.
- The Critic remains independent and hard safety checks override every model.
- Member 2 can turn a credential-free intent into exactly one real GitHub result.
- Member 3 can run the same frozen evaluation against base and adapter and replay events through the
  existing frontend compatibility gateway.
- Runtime tests, health, ten-run latency evidence and two final rehearsals pass on the demo machine.

## Merge and handoff checklist

1. Work on `member1/runtime`; do not edit `src/` or another member's owned path.
2. Publish Pydantic fixtures and canonical event samples at hour 4.
3. Integrate at hours 10, 18, 26 and 30; never force-push a consumed checkpoint.
4. For every contract change, send exact JSON plus Pydantic and consumer impact before merge.
5. For the adapter handoff, verify manifest hashes with Member 3 before touching agent defaults.
6. Before merge, run `pytest runtime/tests -q`, `python -m helios.health`, and Member 3's fast eval shim.
7. After the final merge, complete one real fast task, one real deep task and one adapter-off rollback.
8. Freeze model/agent/adapter selections before the final three Gauntlet runs; any later change invalidates
   those evidence runs.
