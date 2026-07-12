# SOUL.md — Hermes on the Helios Runtime

> Helios is the local agent runtime. Hermes is the multipurpose software-engineering agency powered by
> it. The repository may visually surface the Helios name, but product behavior, policies and external
> work are governed by Hermes.

- **Version:** 2.0
- **Updated:** 12 July 2026
- **Team:** 3 people
- **Primary judged job:** autonomous maintainer-on-duty for a real GitHub repository
- **Additional operating modes:** scoped product builder and defensive repository security auditor
- **Execution principle:** local-first models, typed artifacts, least-privilege tools, independent
  criticism, policy-gated external effects and complete observability

This file is the product constitution. The three `TEAM_MEMBER_*.md` files describe implementation
ownership. When a team README conflicts with this document, this document wins unless all three members
record an explicit scope change here.

---

## 1. Product identity

### 1.1 Helios

Helios is the execution kernel:

- accepts normalized tasks;
- creates per-request typed plans;
- schedules specialist agents and tools;
- manages local models, adapters, memory and budgets;
- persists typed artifacts and trace events;
- routes failed/rejected work through revision or escalation;
- returns credential-free external-action intents.

Helios does not own GitHub credentials, publish vulnerabilities, bypass policy or treat model confidence
as proof.

### 1.2 Hermes

Hermes is the agency/product that uses Helios to perform real software work. Hermes is useful in three
modes while sharing one execution architecture:

```text
maintain        real GitHub intake, triage, fixes, reviews, docs and release drafts
build           scoped brief/feature → requirements → code → tests/security → PR
security_audit  consented repository review → redacted findings → optional remediation PR
```

The maintainer workflow remains the public headline because it has a clear human function, a real live
surface, objective outcomes and fast repeatable tasks. Builder and security modes demonstrate that the
runtime is genuinely reusable rather than tuned to one demo script.

### 1.3 One-sentence description

Hermes is a local-first software agency whose manager plans and delegates work to specialist small
models, validates every result independently, and lands safe, tested, auditable output on real GitHub
repositories.

---

## 2. Current implementation truth

This section separates what already exists from what these plans still intend to build. Do not present
planned behavior as implemented evidence.

### 2.1 Implemented frontend

The root project is an existing Next.js 16 / React 19 / TypeScript application using Tailwind,
Zustand, `@xyflow/react`, React Three Fiber and Bun.

Implemented visual/component surfaces include:

- **Blueprint Canvas** — office/agent nodes and status-oriented visualization;
- **Chat** — prompt entry, streamed messages, agent activity and project file list;
- **God Mode Terminal** — streamed pipeline/terminal messages and local command-style display;
- **Workstation** — generated code artifact viewing and preview component;
- **Cost Dashboard** — token, latency and per-office cost aggregation;
- **Multiverse** — Git branch visualization and controls;
- **Settings** — current GitHub/Vercel connection UI and status.

The main navigation currently exposes only a subset of those components. Workstation, cost and
multiverse components existing in code does not automatically prove they are reachable in the final
demo build. Verify actual navigation before including any surface in evidence.

### 2.2 Frontend scope decision

The visual frontend is accepted as complete and frozen for the current three-person work split.
Therefore:

- no member is assigned a second dashboard, Vite migration, redesign, route tree, new UI kit or visual
  feature build;
- integration work may build backend APIs, a WebSocket gateway, authentication hardening, fixtures and
  automated tests;
- changes to presentation components require a separate explicit team decision;
- a missing screen cannot be described as implemented merely because this document once planned it.

### 2.3 Features not currently proven by the frontend

The current code does not establish the old document's claims of a complete Role Builder wizard,
review queue, prompt/policy editors, run-search page, trace-tree comparison, eval dashboard, alert-rule
editor, model timeline, microphone assignment flow or live voice controls.

Those claims are removed from the committed demo story. Backend records for plans, traces, evals,
alerts, policies and models are still required because they make the system debuggable and testable,
but evidence should use actual logs, reports, GitHub URLs and the surfaces that truly exist.

### 2.4 Backend/model status

At the time of this update, the repository contains the completed frontend and planning documents. The
planned Python runtime, Convex control plane, Cloudflare Worker, model-training pipeline, evaluation
suite and realtime compatibility gateway must be implemented by the three team lanes.

The implementation READMEs must therefore be treated as build contracts, not descriptions of already
working services.

---

## 3. Non-negotiable product invariants

### 3.1 Real completion

A live task is complete only when the intended external artifact exists and its URL is persisted:

- comment or clarification request posted;
- labels/milestone applied;
- exact duplicate closed with a valid link;
- branch/PR opened;
- qualifying PR merged under policy;
- private security report stored or remediation PR opened;
- release created in draft state.

Plans, fixtures, queue rows, generated text, local patches and dry runs are not real completions.

### 3.2 Typed artifact-only handoffs

Agents do not depend on hidden cross-agent chat. Every handoff uses versioned typed artifacts with:

```text
schemaVersion, artifactId, taskId, runId, nodeId, type,
producer{name,version}, upstreamArtifactIds[], policyRuleIds[],
contentHash, content, createdAt
```

Required core artifacts:

```text
plan, classification, dup_report, research, repro_report,
patch, test_result, security_report, review_notes, draft_reply,
critic_verdict, blocked, escalation, release_draft
```

Builder artifacts:

```text
requirements_spec, architecture_decision, implementation_plan,
build_manifest, package_result, deployment_draft
```

Security artifacts:

```text
repository_inventory, dependency_inventory, sbom,
secret_finding, vulnerability_finding, threat_model,
remediation_plan, sarif_report
```

### 3.3 Independent critic

Every outbound artifact is reviewed by a Critic that did not produce it. The Critic checks acceptance
criteria, evidence, policy IDs, schema validity, tests, security results, scope and tone.

Verdicts:

```text
pass     produce a signed credential-free external-action intent
revise   return concrete criterion-level notes to one target node
blocked  produce a context-complete escalation
```

One bounded revision is allowed. Two equivalent critic rejections escalate. Failed deterministic
tests/scans cannot be converted to `pass` by model reasoning.

### 3.4 Least-privilege tools

Each plan node declares time, token and tool budgets. Tool grants must be a subset of the expert's
registered grants and repository policy.

Hard rules:

- repository reads are scoped to the resolved allowlisted checkout;
- file writes are scoped to the task worktree;
- commands use an allowlist, sanitized environment, timeout and output cap;
- arbitrary commands copied from issues/prompts are never executed directly;
- public internet/provider use follows data-egress policy;
- the runtime and browser never receive GitHub App or provider secrets.

### 3.5 Honest telemetry

Every model/tool step records real model, prompt, adapter, tokens, latency, execution location, result,
error and actual cost. Local `$0.000` and estimated cloud-equivalent cost are different metrics and must
never be relabelled.

### 3.6 No autonomous self-training

Failures and human corrections create `pending-review` candidates. They do not automatically become
training records, eval goldens, active prompts or promoted adapters.

---

## 4. Operating modes

### 4.1 Maintainer mode

Declared human job: replace a repository's maintainer-on-duty rotation.

| Human duty | Hermes task | Default lane | External result |
|---|---|---|---|
| Read/classify new work | `intake`, `classify` | Fast | Classification + allowed labels |
| Prioritize/milestone | `label` | Fast | GitHub labels/milestone |
| Detect duplicates | `dedupe` | Fast | Linked notice; threshold-gated close |
| Request missing information | `clarify` | Fast | Specific GitHub reply |
| Answer questions | `respond` | Fast | Evidence-backed reply |
| Reproduce a bug | `repro` | Deep | Deterministic reproduction report |
| Fix a bug | `fix` | Deep | Tested branch/PR; gated merge |
| Review an inbound PR | `review` | Deep | Review comments; gated merge |
| Synchronize docs | `docs` | Deep | Docs patch/PR; qualifying merge |
| Prepare a release | `release` | Deep | Draft release only |
| Hand off exceptional work | `escalate` | — | Full artifact chain + precise decision |

Fast representative flow:

```text
GitHub issue webhook
→ task claim + memory/policy
→ planner
→ triage ∥ dedupe ∥ optional research
→ reply draft
→ independent critic
→ policy/write-back
→ real GitHub URL
```

Deep fix flow:

```text
bug issue
→ plan
→ dedupe ∥ reproduction
→ code expert
→ tests
→ security review
→ critic
→ branch/PR intent
→ GitHub App write-back
```

### 4.2 Builder mode

Builder mode turns a scoped brief or feature request into a reviewable repository change.

```text
brief/repository context
→ requirements + non-goals + open decisions
→ architecture decision
→ implementation DAG
→ web/backend/test/docs/security branches
→ integration worktree
→ full build/test/security checks
→ critic
→ branch/PR intent + build manifest
```

Rules:

- inspect and extend the repository's existing stack before proposing replacement;
- missing product decisions that materially affect auth, payments, privacy, deployment or data shape
  become explicit blockers;
- specialists with overlapping files are serialized through an integration node;
- a code snippet is not a build result; complete files, compile/typecheck/tests and a manifest are
  required;
- branch/PR is the default delivery;
- repository creation, production deployment, paid services and destructive migrations require explicit
  policy and human confirmation.

### 4.3 Security-audit mode

Security audit is defensive, repository-scoped and read-only by default.

```text
repository consent/scope
→ inventory languages/packages/workflows/exposure
→ dependency ∥ secret ∥ SAST ∥ config analysis
→ normalize/dedupe findings
→ evidence/reachability/severity review
→ critic
→ private redacted report
→ optional separately approved remediation
→ tests + rescan + PR
```

Security rules:

- only allowlisted repositories with `securityAuditOptIn` can be scanned;
- external hosts, production services and third-party targets are out of scope;
- no destructive tests or active exploitation;
- a secret value is redacted immediately and never persisted in artifacts/traces/events;
- severity, confidence, exploitability and reachability are separate fields;
- CVE/CWE/advisory claims require authoritative sources and retrieval timestamps;
- public issues/comments for unpublished findings are disabled by default;
- report generation and remediation are separate permissioned actions;
- advisory/release publication is always human-controlled.

---

## 5. System architecture

```text
REAL SURFACES
GitHub issues / PRs / repositories
        │ webhook                                ▲ credentialed result URL
        ▼                                        │
Cloudflare Worker ──verified/normalized task──► Convex control plane
                                                     │
                                                     │ claim + bounded packs
                                                     ▼
                                      On-device Helios runtime
                                      ┌─────────────────────────┐
                                      │ Planner                 │
                                      │ Runtime scheduler       │
                                      │ Model/adapter manager   │
                                      │ Specialist registry     │
                                      │ Worktree/artifact store │
                                      │ Independent critic      │
                                      └─────────────────────────┘
                                                     │
                                    spans/artifacts/intents/results
                                                     ▼
                                             Convex control plane
                                                     │
                              policy-gated GitHub App write-back
                                                     │
                                                     ├─► GitHub
                                                     │
                                                     └─► cursor event feed
                                                              │
                                                   WebSocket compatibility
                                                          gateway :9100
                                                              │
                                                   completed Next.js client
```

### 5.1 Cloudflare Worker

- verifies GitHub `X-Hub-Signature-256` against the raw body;
- deduplicates deliveries;
- suppresses Hermes-authored loops;
- normalizes supported GitHub events;
- enqueues without waiting for inference;
- exposes bounded authenticated hosted-inference/research proxy routes;
- never logs signatures, provider credentials, private bodies or suspected secrets.

### 5.2 Convex control plane

Canonical source of truth for tasks, runs, spans, artifacts, agents, adapters, memory, policies, evals,
alerts, findings, reviews, write-back audits and global controls.

Convex—not the browser or gateway—decides canonical task state, totals and completion.

### 5.3 Helios runtime

- claims work with lease/heartbeat;
- creates and validates typed plans;
- runs independent nodes concurrently;
- manages llama.cpp model servers and adapters;
- enforces budgets/tool grants/workspace isolation;
- resumes from persisted completed nodes;
- buffers trace events during temporary control-plane loss;
- returns intents without receiving external credentials.

### 5.4 Write-back layer

Only component holding GitHub credentials. It enforces repository identity, lease, critic artifact hash,
base SHA, protected paths, required checks, patch limits, security state, idempotency and current pause/
write-back mode immediately before every mutation.

### 5.5 Realtime compatibility gateway

Projects canonical events to the completed frontend. It is stateless apart from bounded connection
buffers and cursors.

Current client boundary:

```text
WebSocket: NEXT_PUBLIC_ORCHESTRATOR_URL (default ws://localhost:9100)
client prompt: {"type":"prompt","data":"..."}
server events: progress, terminal, file, token_usage,
               cost_update, complete, error
```

Gateway requirements:

- validate/authenticate/rate-limit prompt creation;
- deduplicate prompt IDs;
- replay by event cursor after reconnect or provide a snapshot;
- preserve ordering with event ID and sequence;
- never replay ambiguous mutations automatically;
- project redacted fields only;
- label fixture/dry-run/degraded/replayed/live data;
- send completion only after a persisted real result URL exists.

The current client contains inactive envelope/status handling. Do not claim live wrapper subscription or
heartbeat evidence until the final build demonstrably consumes it.

---

## 6. Agent organization

| Role | Default model | Responsibilities |
|---|---|---|
| Planner/Manager | Qwen3-8B Q4 | Context pack, DAG, budgets, delegation, replan/escalation |
| Triage | Qwen3-4B Q4 | Classification, priority, labels, clarification |
| Dedupe | bge-small + Qwen3-4B | Candidate retrieval and evidence-backed duplicate verdict |
| Web/TypeScript | Qwen2.5-Coder-7B Q4 | React/TS/web repository changes |
| Backend/Python | Qwen2.5-Coder-7B Q4 | API/backend/data/code changes |
| Test | Qwen2.5-Coder-7B persona | Reproduction, tests and exact failure reporting |
| Docs | Qwen3-4B | Documentation, release draft and reply drafting |
| Security | Qwen3-4B persona + tools | Scan normalization, defensive review, remediation advice |
| Debug | Qwen2.5-Coder-7B | Stack traces, reproduction and fault isolation |
| Research | Qwen3-4B + controlled proxy | Current upstream/advisory/changelog evidence |
| Critic | Qwen3-8B independent context | Acceptance/policy/evidence gate |

An expert is:

```text
base weights + system/persona + version + minimal tools + budgets + optional promoted LoRA
```

Personas sharing base weights do not require separate full model copies.

### 6.1 Dynamic planning

Different inputs must produce structurally different valid DAGs. A question may use three nodes; a bug
or build may use parallel research/repro/implementation branches; a security audit may use parallel
deterministic scanners before normalization.

### 6.2 Dynamic expert spawning

When no registered role clears the capability threshold, Planner may request a new expert using known
base weights, generated bounded persona, minimal tool grants and a task budget. The role is validated,
persisted with `origin: spawned`, and traced before delegation.

The deterministic evidence case remains a Rust repository task that creates `rust-expert` mid-run.

### 6.3 Role self-adjustment

Repeated normalized critic failures may create a new persona-only version with a visible diff. Automatic
self-adjustment cannot change tools, policies, models, adapters, autonomy or spending. Old versions are
immutable and rollbackable.

---

## 7. Models and LoRA/QLoRA

### 7.1 Runtime model strategy

- Pin hot Planner/Triage/Embedding models when hardware permits.
- Load code experts on demand and LRU-evict cold models.
- Record cold-load time separately from generation.
- Use grammar/schema-constrained decoding for bounded structured output.
- Fallback ladder: local 8B → local 4B → consented Workers AI → consented configured remote model.
- Record every attempted rung and actual hosted cost.

### 7.2 Fine-tuning scope

Train one high-volume Qwen3-4B triage/reply/docs adapter first. Do not begin by tuning Planner, Critic or
the code model.

- QLoRA is the default under constrained VRAM.
- Ordinary BF16/FP16 LoRA is allowed when the exact base fits safely.
- Training uses the original compatible Hugging Face base/tokenizer, not a GGUF file.
- Export PEFT adapter and convert it to a llama.cpp-compatible GGUF adapter.
- Load the adapter separately from the exact GGUF base.
- Keep Planner base-first.
- Never attach the producer adapter to the Critic reviewing that producer's work.

### 7.3 Data governance

Allowed data: reviewed public/licensed issues, PRs, maintainer responses, patches, team-owned history,
manually reviewed synthetic schema cases and approved human-corrected failures.

Forbidden data: secrets, unknown-license content, unreviewed model outputs, live judging inputs, private
content without consent and final Gauntlet cases/goldens.

Freeze manifest hashes and split by repository/thread/time, not random messages. Deduplicate across
splits and preserve provenance, license, reviewer and redaction status.

### 7.4 Adapter promotion

Promotion requires:

- adapter/base/tokenizer hashes and exact compatibility;
- training configuration, library/hardware versions and dataset manifest;
- held-out baseline-versus-adapter report;
- no safety, secret-leak, policy or critical subgroup regression;
- fast-lane latency/memory acceptance;
- three stable final evaluation runs;
- runtime loader smoke test;
- atomic activation plus demonstrated rollback.

If the adapter loses, ship the base model and retain the experiment honestly.

---

## 8. Memory, consent and privacy

### 8.1 Three memory layers

1. **NOW:** task plan, artifacts, tool results and resumable node state.
2. **ENTITY HISTORY:** bounded user, issue, repository, project and security-finding summaries.
3. **BUSINESS POLICY:** current versioned repository policies and consent.

### 8.2 Repository isolation

Repository identity keys all tasks, worktrees, embeddings, policies, memory, findings, artifacts and
write-back actions. Colliding issue numbers or filenames across repositories must never share context.

### 8.3 Consent and data egress

Each task includes repository scope, allowed actions, data classification, allowed cloud providers and
expiry. Private repository content defaults to local-only.

Redact secrets/PII before traces or provider calls. Record every external provider call with purpose,
provider, consent reference, classification, token/byte count and actual cost. Raw voice audio is
discarded after transcription by default.

### 8.4 Retention and deletion

Policies define retention for raw provider payloads, artifacts, entity memory, voice audio, scanner
output and evidence. Private code and suspected secrets receive the shortest retention. Deletion must
remove derived searchable projections without corrupting immutable audit facts.

---

## 9. Autonomy and hard guardrails

### 9.1 Allowed after critic and policy pass

- classification, labels, priority and milestone;
- substantive answers and clarification requests;
- exact duplicate closure above threshold with a link;
- branch/PR creation;
- inbound review comments;
- qualifying small/docs merge with green required checks and repository opt-in;
- draft release;
- read-only defensive security report;
- separately authorized remediation PR.

### 9.2 Escalate by exception

- security-labelled or unpublished vulnerability work;
- breaking API/data changes;
- protected paths;
- low planner confidence;
- missing material product decision;
- two critic rejections;
- failed tests/scanners or base conflict;
- budget/provider/tool breach;
- angry/abusive context;
- possible secret/PII exposure;
- deployment, repository creation or public disclosure.

### 9.3 Hard never

- force-push, branch deletion, repository settings mutation or secret access;
- release/security advisory publication;
- non-allowlisted repository write;
- external/destructive scanning or active exploitation;
- storing or speaking a discovered raw secret;
- bypassing consent, pause, required checks, protected paths, budget or policy;
- auto-promoting prompts, roles or adapters from unreviewed failures.

Enforcement belongs in code, not prompts.

---

## 10. Observability and realtime events

Every step emits a canonical event/span:

```text
schemaVersion, eventId, sequence,
taskId, runId, spanId, parentSpanId, nodeId,
agent, agentVersion, model, quantization,
adapterId?, adapterVersion?, adapterHash?,
promptHash, inputArtifactRefs[], outputArtifactRef?,
tokensIn, tokensOut, costUsd, costCloudEquivalentUsd,
latencyMs, executionLocation, toolCalls[],
status, verdict?, error?, startedAt, finishedAt
```

Minimum operational capabilities, whether exposed through reports/logs/Convex or existing client:

- reconstruct a run tree and plan DAG;
- inspect artifact/tool/test lineage;
- search/filter runs by mode, status, repo, agent and date;
- compare base vs adapter and pass vs fail reports;
- identify cost/latency by agent/model/mode;
- show model load/eviction and fallback attempts;
- retain alert events for failure, cost, latency, lease, eval, adapter and security conditions;
- link a terminal live task to its real GitHub URL.

Do not claim a dedicated frontend screen for these capabilities until it exists and is reachable.

---

## 11. Evaluation and quality gates

### 11.1 Maintainer Gauntlet

Minimum 40 held-out cases:

- 25 triage/dedupe cases;
- 8 response/clarification/docs cases;
- 7 fix/repro cases with objective repository tests.

Targets: triage ≥85%, response ≥85%, fix ≥70%, overall ≥85%, plus three stable final runs.

### 11.2 Builder suite

Minimum 15 cases:

- requirements/architecture constraint coverage;
- multi-file implementation across at least two stacks;
- integration/package/build-manifest cases.

Hard scoring precedes model judging: patch applies, builds/typechecks, tests pass, requested behavior is
met, scope is respected and no secret is introduced.

### 11.3 Security suite

Minimum 20 defensive cases:

- vulnerable dependencies;
- true/false secret fixtures;
- SAST/config findings and false positives;
- reachability/severity distinctions;
- remediation plus rescan;
- authorization refusals.

Track precision/recall/F1, false-positive rate, secret-leak count, unsupported advisory claims and
remediation success. Any raw-secret leak or unauthorized action is an automatic failure.

### 11.4 CI gate

Changes to runtime, agents, adapters, policy, training or evals run the appropriate suites. CI blocks
below thresholds and retains machine-readable reports. Human-corrected failures become reviewed
pending cases through an audited process.

### 11.5 Version story

```text
agents-v1  honest base/prompt baseline
agents-v2  improved prompt/persona
agents-v3  LoRA/QLoRA candidate
agents-v4  best validated configuration; may be base-only
```

---

## 12. Cost, latency and hardware

Fast maintainer target:

| Stage | Target |
|---|---:|
| Webhook, enqueue and claim | 3 s |
| Planner | 6 s |
| Triage/dedupe/research in parallel | 14 s |
| Reply | 12 s |
| Critic | 6 s |
| Write-back | 3 s |
| **Total target** | **44 s** |

Hard acceptance target is under 60 seconds warmed for the representative fast task. Deep fixes,
builder tasks and full security audits are minutes-scale and must be reported honestly.

Demo machine target: RTX 4060-class 8 GB+ VRAM or an equivalent 16 GB+ unified-memory machine. If one
GPU is shared, training stops before inference benchmarks and judging.

---

## 13. Technology decisions

| Layer | Decision |
|---|---|
| Existing frontend | Next.js 16, React 19, TypeScript, Tailwind, Zustand, `@xyflow/react`, React Three Fiber |
| Frontend package manager | Bun; committed lockfile is `bun.lock` |
| Realtime compatibility | WebSocket gateway on port 9100 projecting canonical cursor events |
| Runtime | Python 3.12, asyncio, FastAPI, Pydantic, HTTPX |
| Local inference | llama.cpp server mode, GGUF, grammar/schema-constrained output |
| Models | Qwen3-8B/4B, Qwen2.5-Coder-7B, bge-small or verified compatible inventory |
| Fine-tuning | Transformers + PEFT + TRL + bitsandbytes; GGUF LoRA export for llama.cpp |
| Control plane | Convex |
| Ingress/fallback proxy | Cloudflare Worker |
| Real external surface | GitHub App, REST/webhooks/Git Data API |
| Research/advisories | Controlled Linkup/approved-source proxy with citations |
| Voice | ElevenLabs server-side only when consented; text fallback always |
| Evaluation | Python/pytest harness + GitHub Actions blocking reports |

No Vite/pnpm dashboard migration is planned. Docker, SQLite and a full cross-platform support matrix are
outside the hackathon core.

---

## 14. Canonical data model

Required durable entities:

```text
tasks, runs, spans, artifacts,
agents, adapters, repositories,
entities, policies,
evalCases, evalRuns,
securityFindings, scanRuns, sbomRefs,
reviewItems, alertRules, alertEvents,
writebackActions, providerCalls,
approvedBacklogBatches, systemState
```

Every external mutation has an idempotency key, policy decision, artifact hash, repository identity,
status and result URL/error. Every adapter promotion has base/tokenizer/adapter hashes, dataset/eval
references, active role list and rollback predecessor.

---

## 15. Three-person implementation ownership

### Member 1 — Runtime and agent execution

- Python runtime, local APIs and Pydantic mirror;
- Planner, DAG scheduler, artifact handoffs and critic loop;
- maintainer, builder and security execution lanes;
- worktrees, safe tools, models/adapters and telemetry;
- spawn, self-adjustment, resume/outbox and runtime reliability.

Detailed contract: `TEAM_MEMBER_1_HELIOS_RUNTIME.md`.

### Member 2 — Control plane and external integrations

- canonical contracts, Convex and Cloudflare Worker;
- GitHub App, leases, memory, policy and write-back;
- repository/consent/data-egress isolation;
- findings, alerts, provider proxy, adapter registry and CI;
- Bun/root orchestration and live service operations.

Detailed contract: `TEAM_MEMBER_2_CONTROL_PLANE.md`.

### Member 3 — Model quality and proof

- dataset governance and LoRA/QLoRA training;
- adapter export/model cards/promotion evidence;
- maintainer, builder and security evaluation suites;
- WebSocket compatibility gateway;
- E2E reliability, benchmarks, evidence and rehearsals.

Detailed contract: `TEAM_MEMBER_3_OPERATOR_EXPERIENCE.md`.

Each member has the same 36-hour schedule: about 30 hours owned implementation plus 6 hours shared
integration/evidence/rehearsal.

---

## 16. Demo and evidence plan

The demo uses only reachable, working surfaces.

### Primary maintainer demonstration

1. Show GitHub repository and current allowed policy/write-back mode.
2. Mentor files a real issue or the operator submits its URL through the working prompt path.
3. Existing Chat/Terminal surfaces show honest streamed progress via the gateway.
4. GitHub receives the substantive response/labels or PR.
5. Open the real result URL and corresponding canonical run/report.
6. Show actual latency, model/adapter identity and cost from stored telemetry.

### Builder proof

- submit a small scoped feature against an allowlisted repository;
- show requirements, implementation progress and code artifacts where reachable;
- open the real tested PR and build manifest;
- show that missing deployment/secret decisions escalate instead of being invented.

### Security proof

- run read-only audit against an allowlisted fixture/real repository with consent;
- show redacted normalized findings and tool/version evidence;
- prove zero write-back during the read-only run;
- separately authorize one remediation and open a tested PR;
- show before/after scan delta without publishing sensitive details.

### Required evidence index

- exact task/run IDs and commit/model/adapter/policy versions;
- real GitHub URLs;
- critic revise→pass and blocked/escalated examples;
- spawned expert example;
- baseline vs adapter report and rollback recording;
- three final Gauntlet runs;
- builder PR/build manifest;
- security report/remediation/rescan evidence;
- actual provider/cost/latency records;
- labelled fallback replay.

Fixtures and recordings must be labelled. They are fallback evidence, never counted as live completions.

---

## 17. Risk register

| Risk | Response |
|---|---|
| Frontend-complete claim exceeds reachable features | Verify final navigation; remove unsupported demo claims rather than invent screens |
| Existing browser token flow conflicts with GitHub App boundary | Disable/replace server flow; keep credentials server-side; never ship PATs to the client |
| WebSocket code has inactive envelope/status path | Gateway supports direct current messages; do not claim live status until demonstrated |
| Backend scope is too large for 36 hours | Build maintainer vertical slice first; one strong builder and one strong security fixture |
| Local models miss 60 seconds | Pin hot set, shorten contexts, parallelize, benchmark adapter/base, use consented fallback honestly |
| QLoRA candidate regresses | Do not promote; ship base and retain report |
| Only GGUF model is available for training | Acquire exact compatible original HF base/tokenizer before training; otherwise keep LoRA as blocked experiment |
| Scanner false positives damage trust | Preserve tool evidence, confidence/reachability, human review and private reporting |
| Secret appears in scan output | Immediate redaction/fingerprint, rotation escalation, automatic evidence-gate failure |
| GitHub/webhook/network outage | Idempotent retry, cursor/outbox replay, valid-lease rules and labelled fallback recording |
| Prompt asks for unsafe deployment/exploit | Policy/tool layer rejects before execution; context-complete escalation |
| Multi-repo context leak | Key every cache/memory/policy/artifact/credential lookup by repository identity and test collisions |

---

## 18. Definition of done

### Existing frontend and gateway

- [ ] Bun install/build/lint succeeds on a clean clone
- [ ] Working navigation surfaces are documented; unreachable components are not used as evidence
- [ ] Prompt → gateway → canonical task works without duplicate creation
- [ ] Progress/terminal/token/cost/completion events render through the current store
- [ ] Reconnect/replay does not duplicate tasks or GitHub actions
- [ ] No browser bundle or response contains GitHub/provider secrets

### Maintainer

- [ ] Real issue becomes a useful reply/labels in under 60 seconds warmed
- [ ] Real bug becomes a tested PR
- [ ] Every declared maintainer task type has a typed plan or complete escalation
- [ ] Critic revision, spawn and exception escalation are reproducible
- [ ] Ten warmed fast runs record latency and actual cost

### Builder

- [ ] Scoped brief produces requirements, architecture, integrated code, tests and security report
- [ ] Result lands as a real PR with build manifest
- [ ] Missing product/deployment/secret decision escalates rather than being invented

### Security audit

- [ ] Read-only audit produces reproducible, normalized, redacted findings with zero mutation
- [ ] Raw secret fixture never appears in persisted/output data
- [ ] Unauthorized exploit/external scan is rejected before tool execution
- [ ] Separately approved remediation produces tested PR and rescan delta

### Models and quality

- [ ] Base model inventory and hashes are recorded
- [ ] LoRA/QLoRA candidate has reviewed dataset manifest, config, model card and checksums
- [ ] Base-vs-adapter report covers quality, safety, latency and memory
- [ ] Critic is independent of producer adapter
- [ ] Adapter promotion/rollback is atomic and demonstrated
- [ ] Maintainer, builder and security suites pass their hard gates in CI
- [ ] Three identical final configuration runs are retained

### Control plane and safety

- [ ] Convex is canonical for tasks/runs/artifacts/findings/policy/evals/audits
- [ ] Webhook HMAC, leases, idempotency and repository isolation are tested
- [ ] GitHub mutations come only from the credentialed policy/write-back layer
- [ ] Global pause, PR-only/dry-run/live modes and emergency stop work
- [ ] Data-egress consent, redaction, retention and provider cost are auditable
- [ ] Hard-never rules are enforced in code

### Evidence

- [ ] Every claimed live completion links to a real external URL
- [ ] Fixtures/replays are visibly labelled
- [ ] Evidence index contains exact versions, IDs, URLs, timestamps and reports
- [ ] Two timed rehearsals complete using the same surfaces/order as judging

---

*Helios plans and executes. Hermes maintains, builds and audits. The Critic validates. Policy decides
what may leave the machine and what may land on GitHub.*
