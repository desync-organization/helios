# Team Member 2 — Control Plane, GitHub, Security Boundaries, and Integrations

## Mission

Own every durable, credentialed, and externally visible part of Hermes. Member 1 produces plans,
spans, artifacts, findings, patches, and write-back intents. You persist them, enforce leases and
policy, execute allowed GitHub actions exactly once, expose canonical realtime records to Member 3,
and keep provider secrets out of the runtime and browser.

Your lane is successful when the same Helios runtime can safely operate as:

1. a GitHub maintainer that triages issues and opens tested fixes;
2. a product-building agency that turns a brief into code, tests, documentation, and a PR; and
3. a repository security auditor that finds, explains, prioritizes, and remediates vulnerabilities
   without leaking secrets or performing unauthorized exploitation.

The public, judged vertical slice remains the GitHub maintainer workflow from `soul.md`. Builder and
security modes reuse the same task queue, artifact store, policy engine, critic gate, audit log, and
write-back layer instead of becoming separate demos.

## Planning baseline — 12 July 2026

- The existing root Next.js frontend under `src/` and `public/` is accepted as complete. Do not build
  another dashboard, create a Vite application, add visual routes/components, or move it into an
  `apps/dashboard` monorepo.
- The repository uses Bun and the current root Next.js project. Replace the old pnpm/Vite assumptions
  in your implementation plan with additive Bun scripts; do not erase the current app.
- Server-only code under `src/app/api/` may be hardened or replaced when required for authentication
  and proxying. That is backend/security work. Do not change presentation components or styles.
- `soul.md` remains authoritative for the Hermes/Helios identity, real GitHub completion, typed
  artifacts, independent critic, observability, memory, latency, autonomy and hard-never rules.
- The frontend-complete declaration is a scope decision, not permission to fake missing data. Member 3
  may verify the frozen client through a compatibility gateway; canonical truth remains in Convex.

## Equal three-person split

| Member | Primary ownership | Interfaces you provide/consume |
|---|---|---|
| **1 — Runtime** | Planner, scheduler, experts, model serving, tools, worktrees, critic | Claims tasks; emits spans/artifacts/intents; consumes memory/policy |
| **2 — You** | Contracts, Convex, GitHub App, Cloudflare, policy, memory, external providers | Canonical source of truth and only credentialed write-back boundary |
| **3 — Model quality** | LoRA/QLoRA, datasets, Gauntlet, gateway, E2E reliability, evidence | Publishes adapters/eval reports; consumes redacted canonical event streams |

Each person has the same 36-hour window: about 30 hours of owned implementation and 6 hours of joint
integration/rehearsal. Do not silently take ownership of runtime algorithms, frontend construction,
training, or eval scoring.

## Repository ownership

You own:

```text
convex/
apps/worker/                    # Cloudflare Worker only; no dashboard app
packages/contracts/
policy/
infra/
scripts/                        # bootstrap, health, seed and demo orchestration
.github/
package.json                    # additive root integration scripts
.env.example
.gitignore
src/app/api/                    # server-only auth/proxy hardening, coordinated changes
```

You do not own:

```text
src/components/, src/app/page.tsx, src/app/globals.css, public/ # completed frontend
runtime/, agents/                                      # Member 1
training/, datasets/, evals/, adapters/, benchmarks/  # Member 3
gateway/, tests/e2e/, evidence/                        # Member 3
```

You own canonical wire contracts but not unilateral contract changes. For every breaking field change:

1. document the exact old and new JSON;
2. bump `schemaVersion`;
3. update shared fixtures;
4. obtain Member 1's Pydantic impact and Member 3's gateway/evaluator impact;
5. merge only after all three contract suites pass.

## Required root commands

Preserve the current commands and add integration commands using Bun:

```bash
bun install --frozen-lockfile
bun dev                         # existing Next.js frontend
bun run build                   # existing Next.js production build
bun run lint
bun run dev:services            # Convex + Worker + runtime + gateway
bun run test                    # TS tests + pytest + fast eval suite
bun run test:contracts
bun run test:integration
bun run demo:seed
bun run demo:check
bun run deploy:worker
```

Do not commit or regenerate `package-lock.json`; Bun's committed lockfile is `bun.lock`. Python remains
an explicit prerequisite installed from `runtime[dev]` and Member 3's quality/training extras.

## Product modes and task contract

Use one task envelope for all modes. `mode` describes the operator's job; `type` describes the unit of
work. Every task is repository-scoped and policy-scoped.

```ts
type HermesMode = "maintain" | "build" | "security_audit";

type TaskType =
  | "intake" | "classify" | "label" | "dedupe" | "clarify" | "respond"
  | "repro" | "fix" | "review" | "docs" | "release" | "escalate"
  | "requirements" | "architecture" | "implement" | "integrate" | "package"
  | "dependency_audit" | "secret_scan" | "sast" | "config_audit"
  | "threat_model" | "vulnerability_triage" | "security_remediate"
  | "role_test" | "eval";

type TaskStatus =
  | "pending" | "claimed" | "running" | "done" | "failed" | "escalated";
```

Minimum task fields:

```text
schemaVersion, taskId, source, mode, type, repo, payload,
status, dedupeKey, requestedBy, consentScope, dataClassification,
policyVersion, lease?, resultUrls[], createdAt, updatedAt
```

`consentScope` must declare repository, allowed actions, allowed cloud providers, whether private code
may leave the device, and expiry. Default private-repository behavior is local-only with no Linkup,
Workers AI, Haiku, ElevenLabs payload, or external security upload until explicit opt-in.

## Shared contracts package

Create focused modules:

```text
packages/contracts/src/
├─ ids.ts
├─ task.ts
├─ plan.ts
├─ artifact.ts
├─ trace.ts
├─ agent.ts
├─ repository.ts
├─ policy.ts
├─ memory.ts
├─ writeback.ts
├─ security.ts
├─ build.ts
├─ adapter.ts
├─ eval.ts
├─ alert.ts
└─ index.ts
```

Use discriminated unions, opaque prefixed IDs, Unix epoch milliseconds and bounded string/body sizes.
Every externally supplied object carries `schemaVersion`. Never expose raw Convex `_id` as a domain ID.

### Required artifact contracts

Support the maintainer artifacts from `soul.md` plus builder and security artifacts:

```text
plan, classification, dup_report, research, repro_report, patch,
test_result, security_report, review_notes, draft_reply,
critic_verdict, blocked, escalation, release_draft,
requirements_spec, architecture_decision, implementation_plan,
build_manifest, package_result, deployment_draft,
repository_inventory, dependency_inventory, sbom,
secret_finding, vulnerability_finding, threat_model, remediation_plan, sarif_report
```

A vulnerability finding must contain:

```text
findingId, scanner, scannerVersion, ruleId, category,
severity, confidence, cwe?, cve?, advisoryUrls[],
repo, commitSha, path?, startLine?, endLine?,
evidenceRedacted, exploitability, reachability,
falsePositiveReason?, recommendedFix, status
```

Never persist a discovered secret value. Store only type, redacted prefix/suffix if policy permits,
location, detector, fingerprint/hash, remediation state and rotation recommendation.

### Required model/adapter metadata

Every model span and promoted agent configuration must be able to reference:

```text
baseModel, baseRevision, baseSha256, quantization,
adapterId?, adapterVersion?, adapterSha256?, adapterScale?,
trainingRunId?, datasetManifestSha256?, promptVersion, agentVersion
```

Promotion metadata comes from Member 3. You persist it and enforce the active pointer atomically; you
do not train, convert or score adapters.

## Convex data model

Convex is the single durable source of truth. Implement indexed tables for:

### `tasks`

```text
taskId, source, mode, type, repo, payloadRedacted, status,
dedupeKey, requestedBy, consentScope, dataClassification,
policyVersion, approvedBacklogBatchId?, lease fields,
resultUrls[], error?, createdAt, updatedAt
```

Indexes: by task ID, status/created time, repo/status, mode/type, dedupe key, updated time.

### `runs`

```text
runId, taskId, mode, repo, lane, status, plannerConfidence,
planArtifactId, start/finish, token totals, actual/equivalent cost,
latency, agentVersions, adapterVersions, fallbackFlags,
resultUrls[], dataEgressSummary, error?
```

### `spans`

Persist parent/node/agent/model/prompt hash, adapter identity, artifact refs, token counts, actual and
cloud-equivalent cost, latency, tool calls, execution location, fallback, verdict and error. Index by
run, parent, agent, model/adapter, status and start time.

### `artifacts`

Store version, type, producer, upstream refs, policy IDs, content hash, redacted searchable projection,
retention class and creation time. Large binaries, repositories, model weights and raw scanner output
belong in approved object storage/workspace; Convex stores verified references and checksums.

### `agents` and `adapters`

Keep all agent versions and origins (`kickoff`, `spawned`, `operator_created`). Keep adapter identity,
base-model hashes, training run, dataset manifest, eval report, promotion status, active roles and
rollback predecessor. A single transaction changes an active adapter pointer.

### `repositories`

```text
repo, githubRepositoryId, installationId, defaultBranch,
visibility, writebackOptIn, securityAuditOptIn,
allowedActions[], allowedCloudProviders[], protectedPaths[],
sizeLimits, requiredChecks[], activePolicyVersion,
retentionPolicy, lastWebhookAt?, health, updatedAt
```

Only server actions read installation/repository IDs. Operator projections are redacted.

### Other required tables

```text
entities, policies, evalCases, evalRuns,
alertRules, alertEvents, reviewItems,
writebackActions, approvedBacklogBatches,
securityFindings, scanRuns, sbomRefs,
adapterPromotions, providerCalls, systemState
```

`systemState` contains global/per-agent pause, emergency mode, write-back mode, security scan mode,
current agent tag, current adapter pointers and update time.

## Runtime HTTP boundary

All `/runtime/*` endpoints require constant-time bearer-token validation, schema checks, body limits,
idempotency keys, safe structured errors and rate limits.

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

Claim returns a bounded task, memory pack, policy pack, repository descriptor and lease. It must never
return GitHub credentials or provider secrets. Completion verifies the current lease one final time.

Status behavior:

- `401/403`: hard authentication/authorization failure;
- `409`: idempotent replay or lost lease with a machine-readable reason;
- `413`: oversized payload;
- `422`: contract/schema failure;
- `429`: retry after bounded delay;
- `5xx`: structured retryability, never an HTML page.

## Realtime and gateway boundary

Member 3 owns the WebSocket compatibility gateway. You provide canonical subscriptions/queries and a
cursor-based event feed—not UI-shaped prose.

Required properties:

- monotonic sequence per run plus unique `eventId`;
- snapshot at a cursor gap, replay after reconnect, and deduplication by event ID;
- redacted projections only;
- explicit fixture/dry-run/live labels;
- actual cost kept separate from cloud-equivalent cost;
- adapter/base model and local/remote execution represented honestly;
- result counts only when a persisted real GitHub URL exists.

The gateway may project legacy `progress`, `terminal`, `file`, `token_usage`, `cost_update`, `complete`
and `error` messages for the frozen client, but Convex records remain authoritative.

## Cloudflare Worker and GitHub webhooks

Create a Worker with small modules for raw-body signature verification, event normalization, Convex
ingest, status, provider proxying and scheduled missed-event recovery.

Support:

- `issues`, `issue_comment`, `pull_request`, `pull_request_review`, `workflow_run`, `release`;
- security/advisory/dependency events available to the installed GitHub App and allowed by policy;
- `X-Hub-Signature-256` verification using Web Crypto;
- delivery/action/repository deduplication;
- bot-loop suppression using the Hermes marker and bot identity;
- fast acknowledgement without waiting for inference;
- bounded retry to Convex and a dead-letter/audit record when ingest fails.

Never log raw signatures, authorization headers, private issue bodies, patches containing suspected
secrets, or provider prompts/responses.

## GitHub App and write-back service

Only the server-side write-back layer holds GitHub App credentials and mints installation tokens. The
runtime, gateway and browser never receive them.

Support action types:

```text
comment, labels_set, milestone_set, duplicate_close,
branch_and_pr, pr_review_comment, pr_merge,
release_draft, policy_commit, eval_case_commit,
security_issue_draft, security_pr, sarif_upload,
build_branch_and_pr, build_status_comment
```

### Enforcement before every mutation

- repository identity and installation match the allowlisted onboarding record;
- current lease is valid and system/agent pause is off;
- live/PR-only/dry-run mode permits the action;
- independent critic passed the exact artifact hash;
- idempotency key has not already completed;
- base SHA and branch state still match;
- policy action/size/spend limits pass;
- protected paths, security labels and breaking changes follow escalation policy;
- patches contain no detected secret and required tests/checks are green;
- autonomous merge meets repository opt-in, patch-size, CI, security and critic rules.

Hard-never rules enforced in code:

- force-push, branch deletion, repository settings mutation or secret access;
- publication of a release or security advisory;
- writing outside an allowlisted repository;
- active exploitation, destructive scanning or scanning an external target;
- bypassing required checks, consent, protected paths, spend/action limits or a pause switch.

For patch PRs, use the Git Data API with the supplied base SHA and complete post-change contents. Stop
and escalate on a base/path conflict; never overwrite contributor work.

## Mode-specific control-plane behavior

### Maintainer mode

- Ingest real issue/PR work, deduplicate deliveries and maintain contributor/repository memory.
- Permit policy-gated labels, substantive replies, exact duplicate closure, PR creation/review, small
  merges, docs merges and release drafts.
- Count completion only after a terminal GitHub action returns a persisted URL.
- Approved backlog release accepts existing allowlisted issue URLs only; it never creates fake issues.

### Builder mode

- Require an explicit target repository or approved new-repository handoff before any write.
- Persist requirements, architecture decisions, implementation plans, generated files, tests and
  package/build results as separate artifacts.
- Create a branch/PR by default. New repository creation, deployment and production environment changes
  require explicit policy and human confirmation.
- Treat generated code exactly like a maintenance patch: tests, security scan, critic, base SHA,
  protected paths and audit trail are mandatory.
- Store project status and result URLs so the existing frontend can show progress via Member 3's
  compatibility gateway without becoming a second database.

### Security-audit mode

- Default to read-only and local-only. A remediation PR is a separate, confirmed action.
- Record tool versions, repository commit SHA, scan configuration and exclusions for reproducibility.
- Normalize dependency, secret, SAST and configuration results; dedupe by stable finding fingerprint.
- Use CVE/CWE/advisory identifiers only when supported by a primary source; retain links and retrieval
  time. Do not let an LLM invent severity or CVE mappings.
- Store redacted evidence, confidence, reachability and false-positive status. Never store the secret.
- Security-labelled findings enter a restricted review queue. Public issue/comment creation is off by
  default to avoid disclosing an unpatched vulnerability.
- Allowed outputs are a private report, draft advisory, or remediation PR. Publication remains human.

## Policy, consent, privacy, and memory

Own versioned policy files:

```text
policy/triage.yaml
policy/autonomy.yaml
policy/escalation.yaml
policy/voice.yaml
policy/build.yaml
policy/security.yaml
policy/data-egress.yaml
policy/retention.yaml
```

Each rule has a stable ID, description, parameters, severity and version. Validate before activation;
commit through the audited write-back layer; update the Convex mirror only after Git succeeds.

Implement three memory layers:

1. **NOW:** task/run artifacts and resumable state;
2. **ENTITY HISTORY:** bounded user, issue, repository, project and finding summaries;
3. **BUSINESS POLICY:** current versioned repository policy.

Apply retention limits and deletion support to entity history. Private code, voice audio and suspected
secrets have the shortest retention. Discard raw voice audio after transcription by default. Redact
PII/secrets before traces or provider calls. Record every permitted data-egress call in
`providerCalls` with purpose, provider, classification, byte/token count, cost and consent reference.

## External integrations

### Hosted inference fallback

Expose an authenticated bounded proxy. Accept only known model purposes and schema-constrained requests;
reject arbitrary tools/URLs and excessive context. Try Workers AI, then the configured Haiku-compatible
provider only when repository consent permits. Return provider, exact model, tokens, latency, cost and
request ID; never relabel remote work as local or free.

### Research and vulnerability intelligence

Provide a controlled proxy for Linkup and approved advisory sources. Strip secrets/private code, cap
query size, preserve source URLs/retrieval times and log data egress. Research can enrich a finding but
cannot override deterministic scanner/test evidence.

### ElevenLabs

Keep the key server-side. Provide bounded transcription, safe alert speech and standup digest actions.
Require transcript confirmation before task creation, avoid private issue/finding content in speech,
rate-limit alerts and retain text fallback on failure.

## LoRA/QLoRA registry and promotion

Member 3 trains and evaluates; Member 1 loads and serves; you own durable promotion state.

Promotion requires:

- adapter and base/tokenizer hashes;
- reviewed dataset manifest and provenance;
- held-out eval report with safety subgroup results;
- ten-run latency/memory benchmark;
- three stable full Gauntlet runs for the final configuration;
- explicit role list and rollback predecessor;
- Member 3 quality approval and Member 1 compatibility smoke test.

Activation updates an atomic pointer. Rollback restores the predecessor without deleting history.
Closed-loop failures create `pending-review` eval candidates; they never enter a training dataset or
active adapter automatically.

## Evaluation persistence and CI

Member 3 owns cases and scoring. You own persistence and the real blocking workflow.

Capture candidates when a critic blocks, run fails/escalates, human edits/rejects work, maintainer
corrects a label/reply, security finding is marked false-positive, generated build fails CI, or a
Hermes PR is reverted. Store wrong output, correction, versions and source URL with redaction.

Create CI that runs Member 3's evaluator when `agents/**`, `adapters/**`, `policy/**`, `runtime/**`,
`training/**` or `evals/**` changes. It must fail below declared per-mode thresholds and retain the JSON
report. Keep one genuine blocked change as evidence.

## Alerts and operational controls

Evaluate alerts for task/run failure, lease expiry, cost/latency spike, escalation, eval regression,
model/adapter mismatch, scanner failure, secret finding, provider outage and repeated write-back denial.

All alerts appear as durable text events. Voice is optional and safe. Implement global pause,
per-agent pause, `dry-run`, `pr-only`, and `live` write-back modes, security read-only mode, emergency
stop, and adapter rollback. Every dangerous action reads current state immediately before execution.

## 36-hour execution plan

| Hours | Owned outcome |
|---|---|
| 0–4 | Bun/root integration, canonical contracts/fixtures, Convex and Worker skeleton, GitHub App, repository onboarding |
| 4–10 | Task/lease/run/span/artifact persistence, webhook verification, maintainer comment/label vertical slice, canonical subscriptions |
| 10–18 | Branch/PR/write-back gates, builder/security contracts, policy engine, protected paths, scan/finding persistence |
| 18–26 | Memory/retention, multi-repo isolation, adapter registry, review queue, hosted research/inference, backlog, alerts/voice |
| 26–30 | Security/outage/rate-limit/idempotency tests, CI gate, deployment, clean-clone and secret scan |
| 30–34 | Shared integration with runtime, Member 3 gateway/adapters/evals, real maintainer/build/security acceptance runs |
| 34–36 | Two demo rehearsals, service monitoring, frozen config, emergency-mode and rollback readiness |

## Required tests

### Contracts and persistence

- TypeScript fixtures and Member 1 Pydantic mirrors round-trip exactly.
- Unknown versions, invalid unions and oversized/redaction-sensitive content fail clearly.
- Indexed queries cover queue, runs, findings, agents/adapters, reviews and analytics without scans.
- Duplicate spans/artifacts/provider calls/write-backs remain exactly once.

### Webhooks, leases and repositories

- Valid signatures succeed; invalid/missing/replayed deliveries do not duplicate work.
- Bot-authored Hermes events cannot create loops.
- Only one runtime claims a task; expired leases requeue; late owners cannot finish/write back.
- Same issue number/finding fingerprint in two repositories cannot cross memory, policy or credentials.

### Write-back and security

- Non-allowlisted repos, bad base SHA, protected paths, failed tests/critic/security and oversized
  patches block.
- Hard-never GitHub actions are impossible even with forged runtime payloads.
- Security reports never expose secret values; public disclosure is off by default.
- Read-only audits cannot mutate GitHub; remediation requires a separate confirmed intent.
- Idempotent replay returns the original result URL.

### Privacy and providers

- Private/local-only tasks cannot call hosted inference, Linkup or voice with repository content.
- Egress records match actual provider calls and redact payloads.
- Provider failure produces a structured fallback or visible failure—never invented output.
- Raw audio is discarded by default and unsafe speech content is rejected.

### Adapter/eval and operations

- Invalid hashes or failed eval gates cannot activate an adapter.
- Rollback atomically restores the previous adapter and audit record.
- CI blocks below maintainer, builder or security thresholds.
- Global pause/emergency mode blocks the next mutation under concurrent load.
- Fresh-clone Bun build, service start, seed, integration and demo checks pass.

## Definition of done

- Convex is the source of truth for all modes, runs, artifacts, findings, memory, policy and audits.
- Genuine GitHub webhooks enter through verified Cloudflare ingress.
- GitHub effects are allowlisted, policy-gated, idempotent and linked to real URLs.
- Maintainer mode can label/reply/fix; builder mode can produce a tested PR; security mode can produce a
  redacted report and separately approved remediation PR.
- No runtime/browser/gateway process receives GitHub or provider credentials.
- Multi-repo data, installation tokens, memory, findings and policies remain isolated.
- Hosted fallbacks and research obey consent and report actual provider/cost.
- Adapter promotion, eval capture, CI regression blocks and rollback are real and auditable.
- Member 3 can replay canonical redacted events through the completed frontend without Convex truth
  being duplicated in the client.
- Root Bun commands, deployment, monitoring, emergency modes and two rehearsals work from a clean setup.

## Merge and handoff checklist

1. Work on `member2/control-plane`; coordinate any `src/app/api/` server-route change before merge.
2. Publish contracts and fixtures by hour 4; tag every consumed schema checkpoint.
3. Merge checkpoints at hours 10, 18, 26 and 30 after contract/integration tests pass.
4. Give Member 1 endpoint, lease, policy and repository-descriptor changes before merging.
5. Give Member 3 subscription, event, adapter, eval and finding schema changes before merging.
6. Never place a real secret in fixtures, logs, screenshots, Convex seed data or committed env files.
7. Validate one task in each mode under dry-run, then PR-only, before enabling any live action.
8. Freeze contracts, policies, provider order and adapter pointer before final evidence runs.
9. Final acceptance is from a clean clone/profile and a second network path, with rollback and emergency
   stop exercised—not merely documented.
