# Hermes / Helios Productization Roadmap

**Status date:** 13 July 2026
**Product source of truth:** `docs/soul.md`
**Delivery contracts:** `docs/TEAM_MEMBER_1_HELIOS_RUNTIME.md`, `docs/TEAM_MEMBER_2_CONTROL_PLANE.md`, and `docs/TEAM_MEMBER_3_OPERATOR_EXPERIENCE.md`

## Purpose

This is the execution roadmap for turning the current Hermes/Helios implementation into a safe,
repeatable product. It is intentionally stricter than a feature checklist. A feature is complete only
when its contracts, authorization, failure behavior, observability, tests, deployment, runbook, and
real evidence all exist.

The product remains:

- **Hermes:** the software-engineering agency operators and GitHub users interact with.
- **Helios:** the credential-free local runtime that plans and executes specialist work.
- **Primary job:** autonomous maintainer-on-duty for an allowlisted GitHub repository.
- **Additional modes:** bounded product building and defensive repository security auditing.

The existing Next.js frontend under `src/` and `public/` is frozen. This roadmap may require backend
compatibility work and may identify future UI needs, but presentation changes require a separate,
explicit scope decision before implementation.

## Status legend and release levels

- **P0:** blocks live use or creates an unacceptable security/correctness risk.
- **P1:** required for a supported beta and repeatable operation.
- **P2:** required for a mature, scalable product after the beta is stable.
- **Owner 1:** `krishang/` runtime, agents, execution, local model serving.
- **Owner 2:** `Member 2/` contracts, Convex, Worker, policy, GitHub, credentials.
- **Owner 3:** `member 3/` training, evaluation, gateway, E2E proof, evidence.
- **Shared:** a contract, acceptance run, release, or decision involving more than one owner.

Three different readiness claims must remain separate:

1. **Engineering-complete:** code and automated checks pass with deterministic fixtures.
2. **Beta-ready:** real credentials, services, models, observability, rollback, and one live acceptance
   run per advertised mode work in a controlled environment.
3. **Production-ready:** tenant authorization, operational SLOs, incident response, retention/deletion,
   backups, abuse controls, support, legal documents, and repeated live evidence exist.

Nothing in this document changes the `soul.md` rule that a dry run, fixture, queue row, plan, local
patch, or generated preview is not a real completion.

## Current implementation truth

Substantial implementation now exists, but it is not yet a production product.

### Present in code

- A Python runtime with typed plans/artifacts, a DAG scheduler, critic loop, execution services,
  repository checkout, resume support, control polling, an agent reservoir, and model/SLM boundaries.
- A head orchestrator that can inspect the local reservoir, use active handlers, spawn constrained
  templates, and apply initial boundary/safety checks to HTML/CSS/JavaScript output. Standards parsers,
  accessibility, browser, build, and repository-test validation are not yet complete.
- A Convex/Worker control plane with webhook verification, repository-scoped tasks, leases, runtime
  endpoints, event storage, artifacts, findings, controls, write-back reservations, and GitHub action
  handlers.
- A compatibility gateway with prompt deduplication, authentication hooks, replay, event ordering,
  heartbeat, redaction, health, and completion gating.
- Overlapping experimental training/evaluation scaffolding for three narrow Gemma web specialists:
  HTML, CSS, and JavaScript. It is not yet a single governed pipeline and remains pending the canonical
  ownership/model decision.
- Frozen maintainer, builder, and security evaluation fixtures under the Member 3 lane.

### Not yet proven

- Live GitHub write-back remains unverified until deployment credentials are provisioned through
  approved secret stores and a safe end-to-end installation-token check succeeds.
- There are no reviewed HTML/CSS/JavaScript datasets, trained adapters, promoted manifests, model
  weights, or running specialist model servers in this repository.
- The public HTTPS application does not have a production `wss://` gateway endpoint.
- The latest cross-owner changes have not yet completed one consolidated clean-clone verification
  pass.
- No current evidence proves a real maintainer completion, builder PR, private security report,
  remediation PR, three stable model runs, or two final rehearsals on this merged worktree.

## Product decisions that must be recorded

These are product decisions, not implementation details. Record each as an ADR or an explicit update
to `docs/soul.md` before code relies on it.

- [ ] **Deployment model:** local single-operator, managed multi-tenant, enterprise self-hosted, or a
  clearly staged combination.
- [ ] **Tenant boundary:** whether an installation, GitHub organization, repository, or user is the
  primary tenant and billing/security boundary.
- [ ] **Identity and roles:** installation administrator, repository operator, contributor, auditor,
  and support operator; document exactly what each can see and authorize.
- [ ] **Operator authentication:** choose the server-side login/session flow and short-lived gateway
  ticket mechanism. Browser tokens must never be reusable server credentials.
- [ ] **Mode confirmation:** define how repository, mode, allowed actions, provider egress, security
  scope, and expiry are explicitly approved. A prompt alone never grants these permissions.
- [ ] **Frontend scope:** either keep the frozen frontend and use GitHub-native/admin-runbook controls,
  or explicitly authorize the smallest UI changes needed for onboarding, confirmation, and review.
- [ ] **Model strategy:** reconcile the constitution's Qwen maintainer adapter plan with the newer
  Gemma HTML/CSS/JavaScript SLM extension. Updating the official model strategy requires a documented
  product decision; the web SLMs must not silently replace Planner or Critic requirements.
- [ ] **Supported hardware:** minimum CPU/RAM/VRAM, supported operating systems, scanner/tool
  prerequisites, and what happens when the machine cannot host the configured model set.
- [ ] **Provider policy:** approved hosted inference/research/voice providers, supported regions,
  failover order, data classifications allowed to leave the device, and spend ceilings.
- [ ] **Data policy:** retention defaults for prompts, code, artifacts, findings, provider payloads,
  audio, telemetry, and evidence; deletion/export behavior; regional requirements.
- [ ] **Security disclosure:** private report ownership, vulnerability disclosure workflow, embargo,
  remediation authorization, and who may publish an advisory.
- [ ] **Commercial model:** public beta limits, pricing/billing, quotas, support level, SLA, and whether
  cloud inference costs are passed through. These may remain explicitly undecided for a private beta.
- [ ] **Licensing:** verify the licenses and redistribution conditions for every base model, adapter,
  training source, scanner, dataset, and bundled binary.
- [ ] **Canonical ownership/layout:** resolve the overlapping SLM training/evaluation code under
  `krishang/training` and `member 3/training`. Owner 3 remains the governed training/evaluation
  authority; Owner 1 should consume promoted manifests and own serving. Choose one canonical pipeline
  and bridge or migrate deliberately so datasets, case sets, manifests, and promotion logic cannot
  diverge.

## P0 — Blockers before any live mode

### P0.1 Provision and verify credentials

**Owner:** Owner 2 with Shared deployment coordination

- [ ] Inventory every required deployment credential: GitHub App private key, webhook secret, runtime,
  control-plane, gateway, provider-proxy, and client tokens. Issue unique scoped values before live use.
- [ ] Verify the reviewed GitHub App key can mint an installation token for the exact allowlisted
  installation and repository; rotate or revoke credentials according to the deployment policy.
- [ ] Replace secrets independently in Cloudflare, Convex, Vercel, local runtime configuration, and
  gateway deployment; never reuse one token for multiple trust boundaries.
- [ ] Keep the root `.env` for non-secret local coordination values. Put Worker-only credentials in
  ignored service-specific development storage and production secret stores so `next dev`, the
  runtime, and gateway cannot inherit GitHub/provider secrets.
- [ ] Add an explicit allowlist of environment variables passed to every child process. The Worker,
  runtime, gateway, frontend, and model servers should each receive only their required variables.
- [ ] Scan the working tree, Git history, logs, screenshots, generated artifacts, Convex seed data, and
  deployment logs for accidental credential material without printing values into new logs.
- [ ] Add secret rotation and suspected-leak response runbooks.

**Exit evidence:** the credential lifecycle is documented; the reviewed private key parses; a safe
installation-token smoke check succeeds; browser bundles/responses and runtime/gateway environments
contain no server credentials; the secret scan report is retained with values redacted.

### P0.2 Restore repository and dependency hygiene

**Owner:** Owner 2

- [ ] Remove the tracked `package-lock.json`; `bun.lock` is the only JavaScript lockfile.
- [ ] Verify `bun install --frozen-lockfile` on a clean clone and prevent npm/pnpm lockfiles in CI.
- [ ] Keep `.env`, model weights, adapters, workspaces, scanner output, private evidence, and temporary
  credentials ignored. Commit only reviewed examples and cryptographic manifests.
- [ ] Document the current owner-directory layout (`krishang/`, `Member 2/`, `member 3/`) and avoid a
  broad folder move until contracts and CI are stable. If the layout is later normalized, do it as a
  dedicated migration with updated scripts/imports and no feature changes.
- [ ] Add formatting/line-ending policy so Windows development does not create noisy CRLF-only diffs.

**Exit evidence:** clean-clone install and repository hygiene checks pass; no second lockfile or secret
artifact is tracked.

### P0.3 Freeze canonical cross-service contracts

**Owner:** Shared; Owner 2 owns the canonical TypeScript package

- [ ] Reconcile the TypeScript, Pydantic, gateway, evaluator, and stored Convex representations of
  tasks, repositories, plans, nodes, artifacts, spans, events, findings, agents, adapters, policies,
  evals, and write-back actions.
- [ ] Fix the gateway-created task mismatch: `feature` is not a canonical task type, an operator source
  cannot contain undeclared GitHub fields, and operator tasks must not later be projected as GitHub
  webhook tasks.
- [ ] Make `maintain`, `build`, and `security_audit` selectable without inferring authorization from
  prompt text. Preserve `requiresPolicyConfirmation` through task creation and enforcement.
- [ ] Replace externally reachable `v.any()`/unbounded dictionaries with strict, versioned validators.
  Patch payloads must not be able to overwrite immutable IDs, repository identity, mode, ownership,
  lease, or timestamps.
- [ ] Define one error-code contract for authentication, lease loss, idempotent replay, validation,
  size/rate limits, policy denial, retryable outage, and ambiguous external completion.
- [ ] Publish shared canonical fixtures and verify exact round trips across all three owners. Breaking
  changes require a schema-version bump and coordinated consumer updates.
- [ ] Freeze one evidence/event provenance vocabulary and mapping. Reconcile runtime event labels
  (`live`, `dry-run`, `degraded`, `replayed`, `fixture`) with evidence classes such as rehearsal and
  fallback, and define `countsAsCompletion` so replay/fallback/fixture data can never inflate live
  completion while a replayed view of a previously verified live result remains traceable.

**Exit evidence:** one fixture corpus round-trips through TypeScript, Pydantic, Convex, and gateway
projection; unknown versions and extra fields fail; all consumers use the same mode/type/source/action
unions.

### P0.4 Bind every runtime write to an active authority

**Owner:** Owner 2 and Owner 1

- [ ] Require a current lease, owner, task, run, repository, mode, and sequence relationship for run
  start, heartbeat, span, artifact, finding, escalation, finalization, and write-back ingestion.
- [ ] Validate that the task is in the expected state and that the run cannot change immutable task or
  repository fields.
- [ ] Revalidate lease, pause, emergency mode, write-back mode, consent expiry, repository health, and
  base SHA immediately before every external mutation—not only when reserving it.
- [ ] Cancel active local work when the lease is lost, global pause/emergency activates, consent
  expires, or the current agent is paused. Cancellation must clean up processes/worktrees safely.
- [ ] Separate administrator/operator control credentials from Worker ingest, runtime, gateway, and
  provider credentials. Record every control change as an audit event.

**Exit evidence:** forged cross-task/run/repository payloads fail; a concurrent pause or lease expiry
blocks the next GitHub mutation; late owners cannot finalize; audit records identify the principal and
policy decision.

### P0.5 Complete exactly-once GitHub write-back

**Owner:** Owner 2

- [ ] Verify immutable GitHub repository database ID, installation ID, owner/name, visibility, default
  branch, permissions, and allowlisted onboarding record server-side before reservation and again
  before mutation. Slug-only/manual seed identity is not sufficient for live use.
- [ ] Bind every outbound field to the exact critic-approved artifact: repository, issue/PR number,
  branch, base SHA, files and encoding, title, body/comment, labels, milestone, duplicate target,
  review location, merge method, draft flag, release tag/target/name/body, and SARIF reference.
- [ ] Either implement and test every advertised action or remove it from contracts/policy until ready.
  In particular reconcile `pr_review_comment`, `pr_merge`, and `sarif_upload` with artifact matching.
- [ ] Add a durable post-GitHub completion journal before acknowledging success. If GitHub succeeds and
  Convex completion fails, a reconciliation worker must retain the external ID/URL and converge the
  original idempotency record without repeating the mutation.
- [ ] Make multi-step Git Data API PR creation recoverable. Record created blobs/tree/commit/ref/PR,
  recognize partial completion, and either resume safely or escalate with the exact external state.
- [ ] Treat every composite action as a saga, including `duplicate_close` (comment then close) and any
  future check/review/merge flow. Persist a receipt for each external step, reconcile before retry, and
  recheck current lease/control/consent immediately before every step.
- [ ] Define canonical patch accounting: normalize POSIX repository paths; reject backslashes, NUL,
  absolute paths, dot/dot-dot segments, aliases and duplicate paths; count UTF-8 bytes rather than
  JavaScript string units; bind exact encoding, content hash, total bytes, file count, and protected
  path decision to the reviewed artifact.
- [ ] Distinguish safe retry, completed replay, in-progress, ambiguous result, policy denial, conflict,
  and permanent failure.
- [ ] Keep release publication, advisory publication, force-push, branch deletion, repository-setting
  mutation, and secret access impossible in code.

**Exit evidence:** fault injection after every GitHub API step converges to one result URL and never
duplicates a comment, branch, PR, close, merge, or release draft; mismatched artifact fields fail before
credentials are minted.

### P0.6 Guarantee ordered, resumable event delivery

**Owner:** Owner 1, Owner 2, and Owner 3

- [ ] Once a lower-sequence durable record is pending, queue later records behind it rather than
  posting higher sequences live.
- [ ] Persist per-run sequence state and per-node completion before acknowledging the next layer. A
  crash mid-layer must not repeat completed artifacts/spans.
- [ ] Make outbox replay idempotent across restarts and quarantine malformed/permanently rejected
  records without silently discarding valid successors.
- [ ] Add cursor-gap detection plus a bounded snapshot/replay protocol. Persist client/upstream cursors
  in the control plane rather than relying only on gateway memory.
- [ ] Never replay a mutation command after an ambiguous disconnect.

**Exit evidence:** injected network loss, process restart, duplicate events, out-of-order events, a
poison record, and cursor loss all recover with ordered projections and no duplicate task/action.

### P0.7 Put the gateway on a production trust boundary

**Owner:** Owner 3 with Owner 2 authentication support

- [ ] Resolve the frozen-client authentication/reconnect gap before implementation. Either approve a
  narrow integration-only exception in `src/lib` for ticket acquisition, client message ID, cursor
  acknowledgment, deduplication, and the exact supported projections, or implement a fully server-side
  same-site cookie/session-resume design that requires no client change. Documentation alone cannot
  satisfy this gate.
- [ ] Deploy the gateway behind TLS and set the production client to an approved `wss://` URL. An HTTPS
  application must not depend on `ws://127.0.0.1`.
- [ ] Use an authenticated server-issued, short-lived WebSocket ticket bound to principal, tenant,
  repository scope, permissions, expiry, and nonce.
- [ ] Scope every event subscription by authorized installation/repository/task. A read-only client
  must not receive the global redacted event feed.
- [ ] Project real progress, terminal, file, token, latency, model/adapter, actual cost, equivalent
  cost, error, and completion events from canonical records. If the frozen store cannot render a field,
  retain it in the canonical envelope/diagnostic evidence and document the UI limitation; do not
  fabricate or silently discard the authoritative metric.
- [ ] Preserve event ID/sequence and reconnect cursor through the frozen client protocol where
  possible; document any frozen-client limitation honestly.
- [ ] Emit `complete` only after a persisted terminal result URL (or an authenticated private-report
  URL for read-only security work) exists.
- [ ] Close HTTP/WebSocket clients and tasks cleanly; handle all normal disconnect/send exceptions;
  enforce size, rate, idle, and connection limits.

**Exit evidence:** production-origin browser E2E over `wss://` creates one task, receives scoped ordered
events, reconnects without duplication, and displays a persisted real result URL without exposing a
server token.

### P0.8 Prove a safe maintainer vertical slice

**Owner:** Shared

Execute this acceptance run only after every applicable P0.1–P0.15 gate is complete. Its position in
the document does not authorize running live before the later-numbered safety gates.

- [ ] Start from a clean clone/profile and an explicitly allowlisted test repository.
- [ ] Validate the flow in `dry-run`, then `pr-only`, before an operator explicitly enables `live`.
- [ ] Receive one real signed GitHub issue webhook, claim it, execute a nontrivial plan, obtain an
  independent critic pass, reserve one action, post a useful reply/allowed labels, and persist the real
  GitHub URL.
- [ ] Exercise a critic revision, an escalation, duplicate delivery, gateway reconnect, pause, and
  write-back replay in the same release candidate.
- [ ] Confirm the runtime and gateway never receive GitHub/provider credentials.

**Exit evidence:** task/run/artifact/policy IDs, timestamps, commit SHA, model/agent versions, actual
latency/cost, audit decision, and GitHub URL are captured in the evidence index. This is the first point
at which the maintainer path may be called live.

### P0.9 Make inference and deterministic tools real

**Owner:** Owner 1 and Owner 3, with Owner 2 provider support

- [ ] Inventory exact base model IDs, immutable revisions, file hashes, tokenizer hashes,
  quantization, licenses, local paths, llama.cpp version/build, and hardware requirements.
- [ ] Start and probe the configured Planner, Critic, text, coder, and embedding endpoints. Readiness
  must verify actual model identity rather than accepting an HTTP 200 from an unknown server.
- [ ] Make readiness capability-specific. Core maintainer models may be ready while optional web SLMs
  are unavailable; a plan requiring an unavailable role must fail admission or use an explicitly
  allowed fallback, without making unrelated healthy lanes unready.
- [ ] Make physical model lifecycle observable: PID/server identity, cold load, warm reuse, measured
  RAM/VRAM, unload, crash, and restart. Accounting-only eviction is not sufficient.
- [ ] Implement and fault-test the local 8B → local 4B rungs. Keep hosted inference disabled for the
  P0 pilot unless its strict purpose/schema allowlist, scoped invocation, consent/data-classification,
  payload/response validation and redaction, spend reservation, timeout/circuit breaker, attempt audit,
  exact model/tokens/request ID, and actual cost controls are brought forward from P1.8 and pass. Never
  silently fall back to an incompletely governed provider.
- [ ] Pin supported formatter, compiler, test, dependency, secret, SAST, configuration, SBOM, and SARIF
  tools. Readiness must show missing tools as unsupported coverage, never as a clean result.
- [ ] Record scanner name/version, rule database, config/exclusions, command hash, timing, exit code,
  redacted output hash, and repository commit for every deterministic security result.

**Exit evidence:** capability-specific cold/warm/fallback traces and tool/scanner inventories are
stored; unavailable SLMs do not block unrelated core readiness; private/local-only tasks never use a
hosted rung; disabled hosted features fail visibly; a failed or absent test/scanner cannot pass.

### P0.10 Decide and enforce private-repository support

**Owner:** Owner 1 and Owner 2

- [ ] If private repositories are not supported in the first release, reject them during onboarding
  and state that limitation everywhere.
- [ ] If they are supported, provide a credential-free brokered snapshot/checkout path so the runtime
  never receives GitHub installation credentials.
- [ ] Enforce exact resolved SHA, repository identity, per-task worktree/artifact namespaces, symlink
  and path traversal checks, protected paths, environment sanitization, output caps, disk/process
  limits, and network-deny defaults.
- [ ] Require a real OS/container sandbox for untrusted repository-owned processes. If that is not
  available in the pilot, restrict support to explicitly trusted repositories and forbid dependency
  installation, package lifecycle scripts, and repository-owned commands. Proxy environment variables
  alone are not a network sandbox.
- [ ] Define governed dependency preparation: use the committed lockfile, approved package manager and
  exact runtime; verify integrity/signatures where available; isolate caches by tenant/repository;
  record package/registry provenance; require network/provider consent; disable lifecycle scripts by
  default and allow only reviewed exceptions inside the sandbox.
- [ ] Add multi-repository collision, environment exfiltration, fork/process bomb, low-disk, timeout,
  symlink, and mutation-during-test/scan fixtures.

**Exit evidence:** the supported visibility matrix is explicit; every supported private checkout is
credential-free and exact-SHA; cross-repository and sandbox escape fixtures fail safely.

### P0.11 Make webhook acceptance durable

**Owner:** Owner 2

- [ ] Put verified normalized webhook deliveries onto Cloudflare Queues or an equivalent durable queue
  before returning an accepted response to GitHub. A `waitUntil` call alone is not durable acceptance.
- [ ] Persist delivery, app/hook, installation, repository ID, event/action, normalized payload hash,
  attempt, and terminal ingest result without storing forbidden private/raw fields.
- [ ] Configure bounded retries, backoff, poison-message handling, a durable DLQ, replay authorization,
  and alerting. The DLQ must not depend solely on the same unavailable service that caused ingest to
  fail.
- [ ] Harden normalization against unsupported actions and repository rename/transfer. Bot-loop
  suppression must verify the actual Hermes actor/action; a contributor quoting a marker must not be
  able to suppress intake.

**Exit evidence:** an outage immediately after receipt loses zero accepted deliveries; restoring and
replaying produces exactly one task; poison messages are visible and safely replayable.

### P0.12 Replace global bearer trust with scoped identities

**Owner:** Owner 1, Owner 2, and Owner 3

- [ ] Create distinct principals/scopes for webhook ingest, enrolled runtime claim/write, write-back
  executor, provider/research executor, gateway read/task creation, operator administration, and
  emergency break-glass.
- [ ] Bind runtime access to an enrolled instance and use short-lived signed credentials or equivalent
  mutually authenticated identity with rotation and revocation.
- [ ] Validate issuer, audience, subject, scope, expiry, and repository/tenant capability on every
  request. A runtime cannot call admin/provider/external-completion routes; a gateway cannot read global
  events; an ingest principal cannot alter controls.
- [ ] Add tenant/organization identity before more than one customer is supported. Key every durable
  entity and cursor by tenant plus repository, not only a mutable slug.

**Exit evidence:** the auth matrix and negative integration suite pass; revocation works during a live
session; two tenants with colliding repository data cannot observe or affect each other.

### P0.13 Verify quality and completion authoritatively

**Owner:** Owner 2 with Owner 1 evidence

- [ ] Do not trust caller booleans such as `testsPassed`, `securityChecksPassed`, or
  `requiredChecksPassed`. Bind policy to typed immutable test/build/scan artifacts and their exact
  repository commit.
- [ ] Before merge or other check-sensitive actions, query authoritative GitHub Checks/Actions for the
  expected SHA and required check names. Stale, missing, pending, or failed checks block.
- [ ] Require exact duplicate evidence/threshold, repository-valid labels/milestones, merge opt-in,
  patch/spend/action limits, and protected-path policy from the frozen policy snapshot.
- [ ] A successful run/task finalization must reference a completed canonical write-back belonging to
  the same tenant/repository/task/run/action and a validated GitHub result. An arbitrary HTTPS URL or
  dry-run result cannot complete a live task.
- [ ] Define a canonical authenticated URL for a stored private security report and bind it to the
  same task/run/policy. Completion provenance comes from canonical state, never a caller-selected
  `live` label.

**Exit evidence:** forged green fields, unrelated URLs, stale checks, and dry-run results fail; one real
terminal URL is verified for every supported completion class.

### P0.14 Protect private artifacts and execute retention

**Owner:** Owner 2

- [ ] Keep only bounded redacted/searchable projections in Convex. Store large, private, or restricted
  artifacts, SARIF, SBOMs, scanner output, and build packages in approved tenant-scoped object storage
  with checksum, encryption, access control, and TTL.
- [ ] Apply secret/PII detection and projection allowlists at webhook, operator prompt, runtime
  artifact, event, provider request/response, log, error, evidence, and browser boundaries.
- [ ] Implement scheduled expiry for artifacts, provider/scanner payloads, memory, audio, restricted
  reports, gateway cursors, workspaces, and derived indexes.
- [ ] Support repository/tenant export and deletion plus legal hold. Deletion removes derived copies
  within the declared SLA while preserving only the documented minimum immutable audit facts.
- [ ] Produce a deletion receipt and storage inventory; test backup/restore does not resurrect deleted
  searchable data outside policy.

**Exit evidence:** a canary-secret corpus appears nowhere in persisted projections/logs/client output;
artifact retrieval verifies its hash; expiry/export/delete/legal-hold and restore tests pass.

### P0.15 Enforce the real policy and runtime safety kernel

**Owner:** Owner 1 and Owner 2

- [ ] Load an immutable validated policy/consent snapshot with version, hash, stable rule IDs,
  repository identity, actions/providers, budgets, protected paths, expiry, and data classification into
  every task/run and decision. Prove the Git-backed version and Convex active pointer agree; fail closed
  on missing, invalid, stale, or divergent state.
- [ ] Make the effective agent reservoir safe enough for the advertised maintainer path: reconcile
  local reviewed definitions with active/pause/adapter state, prevent remote tool/model expansion,
  enforce capability threshold/minimal tools/budget on spawn, and persist birth before delegation.
- [ ] Complete head/plan/critic invariants required by the selected maintainer flow: connected valid
  DAG, typed lineage, terminal independent critic, deterministic evidence precedence, one bounded
  revision, and complete escalation.
- [ ] Apply deadline, cancellation, lease/pause/emergency handling, per-node durable checkpoints, and
  ordered outbox semantics to every node used by the live flow.
- [ ] Enforce the P0.10 sandbox/trusted-repository restriction and governed dependency preparation for
  every repository-owned build/test command used in the acceptance run.

**Exit evidence:** policy version/hash and matching active pointer appear on every decision; forged or
stale policy fails; the effective reservoir cannot be remotely expanded; restart/pause/lease loss do
not duplicate or leak work; deterministic failures cannot be overridden by model or critic text.

## P1 — Supported beta workstreams

P1 begins only after the relevant P0 exit gates pass. A feature below must move into P0 if it is
advertised in the first live pilot.

### P1.1 Head orchestrator and agent reservoir

**Owner:** Owner 1 with Owner 2 registry state

- [ ] Choose one authoritative, versioned activation model. A safe default is a reviewed local catalog
  plus a control-plane active pointer that may select/pause only pre-approved definitions. Remote state
  must not silently expand tools, models, budgets, modes, or output types.
- [ ] Reconcile local catalog revision, control-plane agent version/tag, adapter pointer, pause state,
  model readiness, and policy revision before planning. Unsafe divergence fails readiness.
- [ ] Make the exact effective reservoir visible to the head and `/roles`: active, paused, unavailable,
  template, spawned, version, capabilities, tools, budgets, modes, artifacts, model, adapter, health,
  and source revision.
- [ ] Enforce the dynamic-spawn rule: spawn only when no active capability clears the reviewed
  threshold. Record the selection score and why existing agents were insufficient.
- [ ] Require spawn requests to specify reviewed base/template, minimal tools, allowed mode/output,
  time/token/tool budget, and policy authorization. Persist the definition and birth event before use.
- [ ] Retain the deterministic Rust fixture proving `rust-expert` discovery, creation, restart restore,
  execution, and denial of excessive tools.
- [ ] Permit only reviewed persona-only self-adjustments from normalized repeated failures. Never
  auto-change tools, policy, model, adapter, autonomy, or spend; keep immutable rollbackable versions.
- [ ] Block reservoir reload during active runs and make activation atomic after current work drains.

**Acceptance:** the head sees and can use the exact executable reservoir; paused/unready agents are not
planned; unauthorized remote expansion and unnecessary spawn fail; restart restores spawned state and
does not duplicate birth events.

### P1.2 Planner, scheduler, critic, and resume correctness

**Owner:** Owner 1

- [ ] Use schema-constrained model planning for real mode, with one bounded repair and an honestly
  labelled typed fallback. Different tasks must produce structurally appropriate DAGs.
- [ ] Validate cycles, missing dependencies, disconnected nodes, terminal coverage, security paths,
  artifact types, tool grants, budgets, and independent critic ancestry before execution.
- [ ] Apply the end-to-end consent deadline to claim handling, checkout, planning, every node/tool,
  revision, intent creation, finalization, and cleanup. Recheck before irreversible effects.
- [ ] Persist node-level checkpoints instead of only completed layers. A crash must resume without
  repeating completed model/tool work, artifacts, spans, or costs.
- [ ] Make cancellation safe: stop child processes/model calls, preserve diagnosable evidence, restore
  worktrees, and release resources on lease loss, pause, timeout, shutdown, or operator cancellation.
- [ ] Give the Critic all relevant upstream artifact hashes and deterministic results while preserving
  independent model/persona/adapter configuration.
- [ ] Keep one bounded criterion-level revision. Two equivalent rejections must yield a complete
  escalation with attempts, smallest failing case, lineage, and precise decision needed.
- [ ] Ensure deterministic tests/scans, base conflicts, protected paths, and secret detection override
  all model confidence or critic prose.

**Acceptance:** malformed plans fall back visibly; parallel nodes overlap; per-node budgets terminate;
restart is idempotent; critic revise→pass and double-rejection escalation are reproducible; no expired
task can submit an intent.

### P1.3 Execution, workspace, and repository safety

**Owner:** Owner 1

- [ ] Enforce complete-file or base-SHA-bound structured patches; verify patch hash, total size, file
  count, encoding, protected paths, symlinks, and repository ownership before materialization.
- [ ] Apply specialists in dependency order to one isolated worktree. Overlapping parallel file edits
  must serialize through an integration node.
- [ ] Run only repository-declared commands from a curated policy, never commands copied from a prompt
  or issue. Sanitize environment, working directory, network, timeout, process tree, and output.
- [ ] Detect unexpected workspace mutation during read-only tools/tests/scans and fail the evidence.
- [ ] Add disk quotas, workspace retention/deletion, orphan process cleanup, orphan worktree recovery,
  and artifact garbage collection tied to policy.
- [ ] Produce complete reproducible test/build/scan records. Failed commands remain failed regardless
  of model interpretation.

**Acceptance:** traversal, protected-path, symlink, command-injection, environment-leak, oversized patch,
mutation-during-scan, timeout, and cross-repository fixtures fail; a deep bug reproduction fails before
the patch and passes after it.

### P1.4 Runtime model serving and telemetry

**Owner:** Owner 1 with Owner 3 promotion packages

- [ ] Make the model manager own or explicitly supervise real llama.cpp processes. LRU eviction must
  release physical memory, not only remove an accounting record.
- [ ] Add hardware-aware admission control and real GPU telemetry through the available platform
  interface. Prevent training from competing with release/demo inference.
- [ ] Trace base model/revision/hash, quantization, prompt version/hash, agent version, adapter
  ID/version/hash/scale, training run, tokens, cold/warm latency, execution location, measured memory,
  actual cost, equivalent cost, fallback attempts, and errors on every model span.
- [ ] Verify a producer's adapter cannot be inherited by the Critic.
- [ ] Add bounded batching/prefix caching only after isolation and correctness tests pass.
- [ ] Provide one-command adapter-off rollback and server crash/backoff recovery.

**Acceptance:** exact identity mismatch fails readiness; cold load, warm reuse, shared allocation,
physical eviction, crash recovery, fallback, adapter use, and rollback are demonstrated within the
hardware ceiling.

### P1.5A Constitutional maintainer adapter program

**Owner:** Owner 3 for data/training/evaluation, Owner 1 for serving, Owner 2 for promotion state

Unless `docs/soul.md` is explicitly amended, the first governed fine-tuning program remains the
Qwen3-4B triage/reply/docs adapter. The Gemma web SLMs are additional specialists and may not silently
take priority over this constitutional requirement.

- [ ] Build a reviewed licensed triage/reply/docs dataset with the required provenance, consent,
  reviewer, redaction, repository/thread/time split, deduplication, and held-out exclusion.
- [ ] Establish honest `agents-v1` base/prompt and `agents-v2` prompt/persona baselines before training.
- [ ] Train reproducible QLoRA/LoRA candidates from the exact compatible Hugging Face base/tokenizer;
  export PEFT and llama.cpp GGUF LoRA artifacts with exact hashes and a model/dataset card.
- [ ] Compare `agents-v1` through `agents-v4` on the frozen maintainer suite, safety subgroups, schema,
  latency, RAM/VRAM, cold/warm behavior, tokens, and actual cost. Keep Planner base-first and Critic
  independent of the producer adapter.
- [ ] Promote only after meaningful improvement, no safety/policy/subgroup regression, fast-lane
  acceptance, three stable full runs, runtime loader proof, atomic activation, and rollback.
- [ ] If the adapter loses, retain the report and ship the base configuration honestly.

**Acceptance:** the constitutional adapter path is either completed with exact promotion/rollback
evidence or superseded by a reviewed `soul.md` amendment before Gemma work is prioritized.

### P1.5B HTML, CSS, and JavaScript SLM program

**Owner:** Owner 3 for data/training/evaluation, Owner 1 for serving, Owner 2 for promotion state

The three web SLMs are narrow adapters over a reviewed student base, not three uncontrolled copies of
an LLM. They are not product features until all steps below pass, and they follow P1.5A unless the
product constitution is explicitly amended.

#### Base and training prerequisites

- [ ] Replace every `REPLACE_WITH_REVIEWED_COMMIT` value with an immutable reviewed base/teacher
  revision and record license, tokenizer, model, and local file hashes.
- [ ] Acquire the exact original training base/tokenizer and the compatible GGUF inference base. Never
  train from GGUF or guess compatibility.
- [ ] Pin Python/ML/CUDA/llama.cpp dependencies, training hardware, seeds, sequence length, optimizer,
  scheduler, batch/accumulation, checkpoints, peak VRAM, wall time, and energy/cost estimate.
- [ ] Keep large weights/checkpoints ignored and store only manifests, model cards, reports, and
  checksums in Git.

#### Governed datasets

- [ ] Build separate HTML, CSS, and JavaScript datasets from reviewed licensed/owned examples and
  manually reviewed synthetic cases.
- [ ] Require example ID, role/mode/task, repository/thread grouping, source/license/provenance,
  reviewer/status, consent, redaction result, input/target, safety tags, split, and content hash.
- [ ] Split by repository/thread/time, not random rows. Freeze train/dev/test manifests, remove exact
  and near duplicates across splits, and keep final evaluation cases fully held out.
- [ ] Reject secrets, private content without consent, unknown-license content, unreviewed model output,
  live judging inputs, and Gauntlet goldens.

#### Teacher distillation and training

- [ ] Run the reviewed Gemma teacher only as an offline candidate generator. Quarantine outputs, bind
  teacher identity/revision/response hash, run deterministic role checks and secret/memorization scans,
  and require review before student admission.
- [ ] Train reproducible Gemma student QLoRA candidates for each role; compare the declared rank/module
  configurations and seeds without untracked manual retuning.
- [ ] Select checkpoints from frozen validation evidence, export PEFT adapters, convert to
  llama.cpp-compatible GGUF LoRA, and hash every artifact.

#### Role-specific evaluation

- [ ] **HTML:** standards parser success, semantic structure, accessibility, constraints, and rejection
  of inline scripts, event handlers, unsafe URLs, secret leakage, and memorized content.
- [ ] **CSS:** real parser/linter success, selector scoping, responsive/focus/reduced-motion behavior,
  remote import/unsafe URL rejection, integration, and visual regression where deterministic.
- [ ] **JavaScript:** real parser/linter/bundler success, browser/jsdom behavior, cleanup/null/error
  handling, CSP/network constraints, dynamic-code rejection, integration, and deterministic tests.
- [ ] **All roles:** same held-out cases for base and adapter, repository build integration, output
  boundary, safety/policy regression, subgroup results, latency, RAM/VRAM, cold/warm behavior, and
  actual cost.
- [ ] Replace shallow brace/balance checks in the head with tool-backed parsers and repository tests.

#### Promotion, launch, and rollback

- [ ] Bind each promotion manifest to role, base/tokenizer, dataset manifest, training run, adapter,
  evaluator/case set, benchmark, model card, known limitations, predecessor, approver, and timestamp.
- [ ] Require no safety/secret/policy/critical subgroup regression, the declared meaningful quality
  improvement, three stable final runs, runtime load smoke, and atomic control-plane activation.
- [ ] Integrate head spawn with the SLM supervisor: a promoted template may lazily acquire/start its
  exact server; failed preflight leaves it unavailable and produces a clear escalation.
- [ ] Measure real process ownership and VRAM, tear down on partial group failure, recover after crash,
  and demonstrate adapter-off rollback.
- [ ] Ship the base model honestly if an adapter does not win.

**Acceptance:** the head discovers, starts/spawns, invokes, validates, critic-reviews, and safely stops
each promoted specialist; tampered evidence or a hash mismatch fails; three stable base-vs-adapter
reports and rollback evidence exist for every advertised SLM.

### P1.6 Control plane, policy, and durable data

**Owner:** Owner 2

- [ ] Complete strict indexed schemas for every canonical entity in `soul.md`, including immutable
  audit identity and bounded redacted projections. Large files/raw scanner output use approved object
  storage with verified references and checksums.
- [ ] Make every idempotent ingest/action return the original stored result and reject a reused ID with
  different content.
- [ ] Version and validate all policy bundles before activation. Git/policy history and the Convex
  active pointer must converge transactionally and retain rollback.
- [ ] Implement installation/repository onboarding lifecycle: install, repository selection change,
  suspension, deletion, permission change, webhook health, and uninstall cleanup.
- [ ] Verify repository database ID/installation/owner/name/default branch/visibility server-side; do
  not trust prompt-provided URLs or IDs.
- [ ] Add repository preflight for App permissions, webhook, base branch, required checks, protected
  paths, limits, supported tools/languages, runtime/model/scanner readiness, consent, retention, and
  write-back mode.
- [ ] Make global, per-repository, and per-agent pause; emergency stop; dry-run/PR-only/live;
  security-read-only; and adapter rollback durable, audited, and checked under concurrency.
- [ ] Add bounded rate limits/quotas and structured correlation IDs at Worker, runtime, gateway,
  provider, and admin boundaries.

**Acceptance:** an operator can onboard, dry-run, promote to PR-only, pause, rotate credentials, revoke
an installation, roll back policy/adapter state, and uninstall without editing source or raw database
rows.

### P1.7 Maintainer, builder, and security product lanes

**Owner:** Shared

#### Maintainer

- [ ] Cover every declared task type: intake, classify, label, dedupe, clarify, respond, repro, fix,
  review, docs, release draft, and escalation.
- [ ] Implement exact evidence/policy gates for substantive comments, repository-valid labels and
  milestones, exact duplicate closure, branch/PR, review comments, qualifying merge, and draft release.
- [ ] Preserve a warmed fast path under 60 seconds without hiding cold-start or hosted cost.

#### Builder

- [ ] Produce versioned requirements, non-goals, user stories, constraints, open decisions,
  architecture decision, implementation plan, complete files/patches, tests/security evidence, build
  manifest, and one branch/PR intent.
- [ ] Escalate missing authentication, payment, privacy, deployment, data-model, secret, or destructive
  migration decisions rather than inventing them.
- [ ] Run full integration/build/test/security checks after specialist outputs are combined.
- [ ] Keep deployment, repository creation, paid services, and production changes separately confirmed.

#### Security audit

- [ ] Require `securityAuditOptIn`, exact repository/commit, allowlisted scanners, paths/exclusions,
  runtime limit, local/network policy, and separate remediation permission.
- [ ] Inventory languages, manifests/lockfiles, workflows, containers/IaC, entry points, auth boundaries,
  and unsupported coverage before scanning.
- [ ] Normalize findings with tool evidence, stable fingerprints, severity, confidence,
  exploitability, reachability, primary advisory URLs/retrieval time, false-positive rationale, and
  remediation.
- [ ] Treat any discovered credential as compromised: redact immediately, store only fingerprint/type/
  location, recommend rotation, and escalate. Restrict all security artifact projections, not only a
  small type subset.
- [ ] Give read-only audits a canonical authenticated private-report URL and zero mutation. Require a
  separate approved remediation task for patch/tests/rescan/private PR. Never publish an advisory.

**Acceptance:** a live useful maintainer reply/labels, tested deep PR, builder PR/manifest, private
read-only report, and separately approved remediation PR/rescan are persisted with real result URLs.

### P1.8 Memory, privacy, retention, and providers

**Owner:** Owner 2 with Owner 1 context consumption

- [ ] Implement all three memory layers with repository/tenant keys: current run state, bounded entity
  history, and versioned business policy.
- [ ] Demonstrate that memory and policy materially affect a plan while colliding issue numbers,
  filenames, findings, embeddings, and contributors remain isolated across repositories.
- [ ] Define retention classes for raw ingress, artifacts, projections, workspaces, provider payloads,
  findings, audio, eval data, evidence, and immutable audits.
- [ ] Implement deletion/export that removes derived searchable projections and local artifacts without
  corrupting the minimum immutable security/audit facts.
- [ ] Complete consent-gated inference, research/advisory, and optional voice proxies. Use allowlisted
  purposes/models/sources, strip secrets/private code, cap payloads, preserve citations and retrieval
  time, and record provider, consent, classification, bytes/tokens, latency, cost, and request ID.
- [ ] Wire runtime research through the controlled proxy; primary advisory evidence may enrich but
  never override deterministic tests/scans.
- [ ] Keep raw voice audio transient and text fallback available. Do not include private findings or
  issue content in spoken alerts.

**Acceptance:** local-only tasks cannot egress; provider failures are visible; egress records match
real calls; deletion/restore and multi-repository isolation tests pass.

### P1.9 Operator experience and onboarding

**Owner:** Owner 3 and Owner 2; frontend changes require explicit authorization

- [ ] Define the first release matrix: supported repository visibility, modes/tasks, languages,
  scanners, repository size, hardware, providers, autonomy, and known limitations.
- [ ] Implement authenticated GitHub App installation selection and server-side membership/repository
  verification. A prompt URL cannot bypass the installation allowlist.
- [ ] Bind task creation to structured repository identity, mode, allowed actions, consent, policy,
  base ref/SHA, client message ID, user, and expiry. Store idempotency in Convex, not gateway memory.
- [ ] Provide an operator path—initially GitHub-native or admin CLI if the frontend stays frozen—to
  inspect readiness, policy/consent, write-back mode, active tasks/leases, plan/artifacts, critic,
  escalations, private findings, approvals, and result URLs.
- [ ] Require explicit confirmation for security remediation, repository creation, deployment, paid
  provider use, destructive migration, and public disclosure.
- [ ] Document exactly which current frontend surfaces are reachable. Do not claim inactive Canvas
  status, review queues, policy editors, run search, eval dashboard, voice, cost optimization, or
  Multiverse controls as live product behavior.
- [ ] If self-service onboarding/review is required, approve a separate minimal frontend scope and then
  test accessibility, keyboard flow, safety wording, loading/offline/reconnect, empty, blocked, and
  partial-failure states.

**Acceptance:** a new authorized operator can install/select a repository, complete preflight, run a
labelled dry run, enable PR-only, inspect evidence, pause/recover, and uninstall from reviewed steps.

### P1.10 Observability, SLOs, alerts, and operations

**Owner:** Shared

- [ ] Define pilot SLOs and capacity limits for task acceptance, event delivery, reconnect/replay,
  warmed fast-task latency, error rate, model readiness, write-back convergence, and zero duplicate
  mutations/secret leaks.
- [ ] Instrument task/run/node/model/tool/provider/write-back latency and errors, queue/lease/outbox
  depth, cursor lag/gaps/replay, gateway connections/backpressure, model cold/warm/VRAM, scanner
  readiness, actual cost, equivalent cost, and policy denials.
- [ ] Correlate principal/session, tenant/repository, task/run/span/event, artifact, policy, model,
  adapter, provider, and external action without logging sensitive payloads.
- [ ] Add alerts and tested runbooks for outage, lease expiry, outbox backlog, cursor gap, task failure,
  cost/latency spike, model/adapter mismatch, scanner failure, provider outage, secret finding, repeated
  write-back denial, reconciliation backlog, and emergency stop.
- [ ] Separate liveness from readiness. Readiness must check authenticated upstream access and the
  dependencies needed for the currently enabled lanes.
- [ ] Establish immutable builds, staging/production separation, migrations, rollback, connection
  draining, backups, restore tests, disk cleanup, and incident severity/ownership.

**Initial measurable targets:** zero duplicate external mutations; zero browser/provider secret leaks;
representative warmed fast task under 60 seconds for ten consecutive runs; accepted task acknowledgment
p95 at most 2 seconds; canonical event to browser p95 at most 1 second; bounded reconnect/replay p95 at
most 5 seconds. Adjust availability targets only after a measured pilot baseline is retained.

**Acceptance:** dashboards answer health, latency, backlog, current model/adapter, actual cost, failure
mode, and affected repository without raw private payloads; restore, rotation, rollback, and incident
tabletop drills are recorded.

### P1.11 Evaluation, CI, and release gates

**Owner:** Owner 3 for cases/scoring, Owner 2 for blocking CI, Owner 1 for execution hooks

- [ ] Connect the frozen 40 maintainer, 15 builder, and 20 security cases to the real runtime. Scores
  must derive from artifacts, repository state, tool output, and external action logs—not model
  self-report fields.
- [ ] Replace generated-only confidence with reviewed, licensed, immutable repository snapshots and
  goldens. Prove final Gauntlet cases are absent from training manifests.
- [ ] Maintain deterministic hard gates before any qualitative grader: schema, patch apply, build,
  typecheck, tests, requested behavior, scope, secret scan, authorization, security rescan, and
  persisted completion.
- [ ] Enforce `soul.md` maintainer thresholds plus explicit builder gates and security precision,
  recall, F1, false-positive, remediation-success, unsupported-advisory, and authorization metrics.
  A secret leak, unauthorized action, failed required test/scan, or unsupported critical claim is an
  automatic failure regardless of aggregate score.
- [ ] Compare `agents-v1` through `agents-v4` on identical case-set hashes, seeds, repository commits,
  prompts, policy, model revisions, tools, and hardware profile. Retain three stable final runs.
- [ ] Record real tokens, latency, cold/warm state, peak RAM/VRAM, execution location, actual provider
  cost, and cloud-equivalent estimate. Keep these metrics distinct.
- [ ] Make CI path-aware but complete: TypeScript typecheck/contracts/policy, Convex schema/codegen,
  Worker build, Python formatting/type/compile/tests, gateway tests, cross-language fixtures, E2E,
  secret/dependency/SAST/license scans, SBOM, and the appropriate eval suites.
- [ ] Fix the current workflow paths: checks such as `hashFiles('evals/**')`, `pytest evals`, and
  root-level `runtime/training/agents` filters do not cover the actual `member 3/` and `krishang/`
  layout. CI must fail if a safety-sensitive owner directory changes without its gate running.
- [ ] Trigger evals from the PR merge base/path filters rather than assuming `HEAD^`. Pin third-party
  CI actions by immutable commit, use OIDC for deployments, protect `main`, and retain all reports.
- [ ] Add property/fuzz tests for IDs, strict schemas, normalization, paths, redaction, idempotency, and
  every write-back payload field.
- [ ] Add failure injection for webhook queue/DLQ, lease/pause races, process crash, outbox/replay,
  model timeout/OOM, gateway gap, GitHub rate limit/base conflict/partial success, provider outage,
  low disk, scanner failure, and backup/restore.

**Verification discipline:** while implementing, run only the narrow affected checks. Once the P0
changes settle, run one consolidated pass instead of repeatedly running the entire suite. A release
candidate then runs from a clean clone and CI becomes the continuous gate.

**Consolidated command families:**

```text
bun install --frozen-lockfile
bun run lint
bun run build
bun run --cwd "Member 2" check
bun run --cwd "Member 2" check:policies
bun run --cwd "Member 2" test
pytest (krishang runtime suite)
ruff/mypy/pytest (member 3 training, eval, gateway suites)
cross-language contract fixtures
browser/E2E acceptance
secret/dependency/security scans
```

Update the root Bun scripts so one documented release command orchestrates these exact owned suites
without assuming obsolete root `runtime/`, `evals/`, or pnpm/Vite layouts.

**Acceptance:** a clean-clone release gate is green; one intentionally failing safety-sensitive change
is blocked; machine-readable reports and build provenance/SBOM are retained.

### P1.12 Deployment and service operations

**Owner:** Owner 2 for cloud/control services, Owner 3 for gateway, Owner 1 for local runtime/model host

- [ ] Create separate development, staging, and production Convex projects, Worker deployments,
  GitHub App installations/keys, gateway domains, policies, tokens, queues/DLQs, object storage, and
  evidence. Never reuse production credentials or data in tests.
- [ ] Provision a stable TLS/DNS topology for app, Worker, control plane, and WSS gateway. The runtime
  connects outbound; the production browser never connects directly to a private local runtime.
- [ ] Keep infrastructure reproducible and reviewed. Validate required non-secret bindings and secret
  presence/format at deployment readiness without logging secret values.
- [ ] Build immutable artifacts, staged migrations, post-deploy smoke checks, canary/promotion,
  connection draining, and one-command rollback.
- [ ] Register/revoke runtime devices, report version/readiness/hardware/model/scanner state, and define
  supported upgrade/compatibility windows.
- [ ] Define backup scope, encryption, frequency, retention, RPO/RTO, restore procedure, and isolated
  restore drills for Convex/object storage/evidence/configuration.
- [ ] Add scheduled sandbox GitHub synthetic checks, webhook health, retention expiry, reconciliation,
  and provider checks. Label all synthetic work and never count it as customer completion.
- [ ] Freeze contracts, policies, model/prompts, agent tag, adapter pointers, provider order, and case
  set before final evidence. Any change invalidates the final three runs and rehearsals.

**Acceptance:** clean-clone staging deploy, smoke, canary, rollback, runtime re-enrollment, and restore
drill pass; production fails closed when required auth/origin/model/scanner configuration is missing.

### P1.13 Documentation, support, legal, and security program

**Owner:** Shared, with named non-engineering review where applicable

- [ ] Replace README claims such as “complete” or “exactly once” with prototype/in-progress language
  until their P0 evidence exists.
- [ ] Maintain one clean-clone quickstart, system/trust-boundary diagram, configuration reference,
  release matrix, supported hardware/tool matrix, and troubleshooting guide.
- [ ] Publish versioned task/artifact/event/error/cursor/status/write-back contracts, including examples
  with no real credentials/private data.
- [ ] Write runbooks for service start/stop, repository onboarding/uninstall, each mode, consent and
  provider egress, private findings/remediation, model acquisition, SLM training/promotion/rollback,
  scanner updates, outbox/DLQ/reconciliation recovery, pause/emergency, backup/restore, credential
  rotation, incident response, evidence regeneration, and demo recovery.
- [ ] Add `SECURITY.md`, a vulnerability reporting channel, threat model, incident severity/ownership,
  access review, dependency/license policy, subprocessor inventory, and secure development/release
  policy. Resolve or explicitly accept all high-severity threat-model items before beta.
- [ ] Publish pilot terms, privacy notice, data retention/deletion/export policy, acceptable-use policy,
  defensive-security authorization language, model/dataset/scanner licenses, and generated-code/data
  ownership expectations.
- [ ] Define support intake, on-call ownership, response targets, status communication, release notes,
  deprecation notices, and customer offboarding/data deletion.
- [ ] Conduct a credential-rotation drill, incident tabletop, restore drill, and independent security
  assessment before expanding beyond a controlled pilot.

**Acceptance:** a new operator can install, configure, run, inspect, pause, recover, rotate, and
uninstall the supported pilot from reviewed documentation; a repository owner can understand every
permission, data flow, retention rule, provider egress, scan boundary, and deletion behavior.

## P2 — General availability and scale

P2 work starts after measured beta usage shows that the P1 architecture and quality gates are stable.

- [ ] Add organization roles, custom role policies, separation of approval duties, SSO/OIDC/SAML,
  SCIM, session/device management, and tenant audit-log export/SIEM integration.
- [ ] Make gateway/event delivery horizontally scalable with durable fan-out, distributed rate limits,
  quotas, backpressure, rolling upgrades, and no missed/duplicate canonical event or external mutation.
- [ ] Add fair scheduling by tenant/repository/lane/capability, noisy-neighbor isolation, cancellation,
  budgets, regional/runtime affinity, and capacity admission.
- [ ] Add signed agent/adapter catalogs, signed runtime/release updates, provenance attestations,
  compatibility windows, canary/shadow evaluation, and automatic rollback on monitored regression.
- [ ] Add customer-managed keys/BYOK, private networking, regional/data-residency options, configurable
  retention, and enterprise export/deletion where market requirements justify them.
- [ ] Define multi-region recovery, replicated backups, formal RPO/RTO, regular disaster-recovery
  exercises, and error-budget-driven release policy.
- [ ] Add GitHub Marketplace lifecycle, permission-drift checks, safe installation-token caching,
  secondary-rate-limit handling, rename/transfer recovery, and decide GitHub Enterprise Server scope.
- [ ] Add privacy-safe product analytics with opt-out and no repository-content capture.
- [ ] Add usage metering, quotas/budget alerts, provider invoice reconciliation, pricing/billing or
  enterprise usage reports without labelling equivalent local cost as billed cost.
- [ ] Add formal support/SLA tiers, public status/history, localization where needed, and a broader
  accessibility conformance review.
- [ ] Complete the applicable assurance program, recurring penetration tests, vendor risk reviews,
  access reviews, SBOM/provenance publication, and incident exercises.
- [ ] Expand models, languages, scanners, providers, repository sizes, or autonomy only through a
  versioned contract, threat review, eval coverage, canary, documentation, SLO, and rollback.
- [ ] Build a reviewed feedback queue for human corrections. Candidates remain `pending-review` until
  licensed, redacted, deduplicated, and approved; no automatic trace-to-training path is allowed.

**GA acceptance:** tenant isolation, authorization, reliability, security, privacy, legal, support,
quality, billing (if enabled), and disaster recovery are independently reviewed; the published SLA and
RPO/RTO are demonstrated; every supported capability has an owner, runbook, SLO, eval, and rollback.

## Delivery sequence and exit gates

Work should follow this order because later proof is invalid if an earlier trust boundary changes.

| Gate | Outcome | Required exit evidence |
|---|---|---|
| **G0 — Containment** | Deployment credentials verified; environments separated; Bun-only repository restored | Credential-lifecycle record, redacted environment-boundary test, clean secret/lockfile scan |
| **G1 — Contract freeze** | One strict task/artifact/event/agent/adapter/finding/write-back protocol across all owners | Versioned golden fixtures, cross-language round-trip report, stable error-code matrix |
| **G2 — Durable safety core** | Scoped identities, lease-bound ingestion, durable webhook/outbox, exactly-once reconciliation, private artifact controls | Negative authorization tests, outage/replay results, failure-injection report, retention/deletion proof |
| **G3 — Local release candidate** | Runtime, reservoir, models/tools, scheduler, critic, resume, controls, gateway projection work deterministically | Consolidated clean-clone report, cold/warm/model/tool inventory, no-secret E2E fixture |
| **G4 — Deployed maintainer pilot** | Signed GitHub webhook to real useful reply/labels and one tested fix PR through public WSS | Real task/run IDs and GitHub URLs, ten warmed runs, pause/reconnect/replay evidence |
| **G5 — Multi-mode beta** | Builder PR/manifest and private read-only security report plus separately approved remediation PR | Real URLs, build/test/security artifacts, zero-mutation audit, rescan delta |
| **G6 — Specialized models** | Reviewed training data, trained/evaluated/promoted SLMs, exact serving, rollback | Dataset/model cards, hashes, base-vs-adapter reports, three stable runs, loader/rollback proof |
| **G7 — Supported beta** | Onboarding, operations, SLOs, alerts, backups, support, privacy/legal and incident processes work | Pilot release manifest, load/restore/rotation/tabletop results, reviewed docs and support owner |
| **G8 — GA** | Multi-tenant scale, enterprise controls, assurance, SLA, DR and commercial operations are proven | Independent review, penetration/compliance reports, RPO/RTO and SLA evidence |

The critical dependency chain is:

```text
credentials and product decisions
→ canonical contracts and scoped identities
→ durable ingest/lease/outbox/write-back correctness
→ runtime/model/tool readiness
→ authorized WSS projection
→ one real maintainer result
→ builder/security acceptance
→ SLM promotion and repeatable quality
→ supported beta operations
→ scale and GA governance
```

## Immediate execution queue

This is the recommended order for the next implementation pass.

1. [ ] **Owner 2:** provision and verify scoped deployment credentials, validate the reviewed GitHub
   App key, and split service secrets from root/frontend configuration.
2. [ ] **Owner 2:** remove `package-lock.json`, fix ignore/env boundaries, and correct README/current
   verification claims so they describe a prototype rather than completed live behavior.
3. [ ] **Shared:** decide the first pilot topology, tenant boundary, supported repository visibility,
   operator auth, mode confirmation, frontend scope, provider policy, and canonical SLM pipeline owner.
4. [ ] **Shared:** freeze strict contracts and golden fixtures; fix task type/source/mode/confirmation,
   trace/model metadata, action unions, error codes, and current CI path drift.
5. [ ] **Owner 2:** introduce scoped machine/operator identities and bind every runtime/admin/gateway/
   provider route to principal, tenant, repository, lease/run capability, and audit actor.
6. [ ] **Owner 2:** make webhook receipt durable with queue/DLQ and harden repository installation/event
   identity plus bot-loop behavior.
7. [ ] **Owners 1/2:** enforce cancellation/deadlines and immediate lease/control checks; make event
   outbox and per-node resume ordered and idempotent.
8. [ ] **Owner 2:** finish full artifact-to-action binding, authoritative checks/completion, durable
   post-GitHub reconciliation, and resumable multi-step GitHub actions.
9. [ ] **Owners 1/3:** install and inventory real base models, llama.cpp, test/scanner prerequisites,
   physical lifecycle/VRAM telemetry, local fallback ladder, and an explicitly disabled-or-fully-
   governed hosted rung.
10. [ ] **Owners 2/3:** deploy authenticated repository-scoped WSS, strict event projections, snapshot/
    cursor replay, and production-origin browser connectivity.
11. [ ] **Shared:** run the single consolidated clean-clone/type/contract/test/security/E2E pass and fix
    every hard failure. Do not proceed on a waived hard gate.
12. [ ] **Shared:** run `dry-run → pr-only → live` for one real maintainer issue, then capture the real
    result URL and ten warmed latency/cost runs.
13. [ ] **Shared:** complete a real tested deep fix PR, builder PR/manifest, read-only private security
    report, and separately authorized remediation PR/rescan.
14. [ ] **Owner 3 with Owners 1/2:** complete the constitutional Qwen maintainer adapter program first
    unless `soul.md` is explicitly amended; then build/review datasets, train/evaluate/export/promote
    the three web SLMs, integrate head-controlled server lifecycle, and demonstrate rollback.
15. [ ] **Shared:** freeze the configuration, run three identical full evaluations, complete two timed
    rehearsals, validate evidence, and only then declare the supported pilot/beta ready.

## Evidence package required for every release claim

Choose one canonical evidence root—currently `member 3/evidence/`—and do not create competing indexes.
Each evidence entry must include:

- evidence ID, data classification, canonical provenance (`live`, `dry-run`, `degraded`, `replayed`,
  `fixture`) plus mapped evidence class (`rehearsal`/`fallback` where applicable), and an explicit
  `countsAsCompletion` value;
- repository identity, base/result commit SHA, task/run/span/artifact IDs, policy/consent version, and
  external action ID/URL;
- agent, prompt, model, quantization, adapter and training versions/hashes;
- tool/scanner versions, configs, command/output hashes, test/build/scan results, and critic verdict;
- actual start/finish/latency, tokens, local actual cost, cloud-equivalent cost, provider calls/cost,
  execution location, and hardware profile;
- dataset/eval/case-set hashes for model claims;
- capture timestamp, source commit, reviewer, redaction result, retained file hashes, and known
  limitations.

Minimum retained evidence:

- [ ] Signed webhook → useful maintainer reply/labels → real URL.
- [ ] Deep reproduction fails before, patch applies, tests/security pass after, PR URL exists.
- [ ] Critic `revise → pass`, second-rejection escalation, and hard deterministic denial.
- [ ] Agent reservoir list, authorized `rust-expert` spawn/use/restart, and denied unauthorized spawn.
- [ ] Different valid DAGs for maintain, build, and security modes.
- [ ] Builder requirements/architecture/code/test/security/build manifest and real PR.
- [ ] Read-only private security report with proven zero mutation.
- [ ] Separately approved remediation patch/tests/rescan/private PR and before/after finding delta.
- [ ] Webhook/control-plane outage, ordered outbox replay, gateway disconnect/reconnect, GitHub partial
  success reconciliation, pause/emergency, lease loss, and provider/model fallback.
- [ ] Ten consecutive warmed fast runs with actual latency/cost.
- [ ] Model cold/warm/load/evict/crash/fallback traces.
- [ ] Base-vs-adapter reports, model/dataset cards, exact promotion manifests, three stable final runs,
  independent Critic configuration, and adapter-off rollback for each promoted SLM.
- [ ] Credential rotation, secret scan, retention/deletion, backup/restore, incident tabletop, and
  release rollback.
- [ ] Two timed rehearsals through the exact release surfaces and service topology.

Evidence validation must reject placeholders, missing local artifacts, changed hashes, unknown schema
versions, unrelated URLs, absent lineage, leaked credentials/private code, and a fixture marked live.

## Product health metrics

Track metrics that show whether Hermes is useful and safe, not just busy:

- repository onboarding completion and time to first successful dry run;
- time to first useful real result and warmed fast-task latency;
- task success, escalation, critic revision, operator rejection, PR acceptance, revert, and duplicate
  external-action rates;
- build/test/security pass rates and false-positive/remediation success by mode/language;
- secret-leak, unauthorized-action, protected-path denial, lease-loss, and reconciliation incidents;
- gateway delivery/reconnect/gap recovery, model readiness/fallback, scanner coverage, and provider
  outage rates;
- actual local/provider cost per completed result, explicitly separate from equivalent cloud cost;
- adapter/base quality, safety, latency, memory, drift, and rollback frequency;
- support volume, incident resolution, retention/deletion SLA, and customer-reported usefulness.

Do not collect private repository content for product analytics. Prefer aggregate counters and hashed/
opaque identities under the documented retention policy.

## Risk register

| Risk | Required response |
|---|---|
| Exposed or over-broad credential | Immediate revoke/rotate, scoped service identity, environment allowlist, secret scan, incident record |
| Duplicate or ambiguous GitHub mutation | Durable external receipt, reconciler, per-step saga, idempotency marker, operator escalation on mismatch |
| Cross-repository/tenant leak | Tenant+repository keys everywhere, scoped auth/cursors/storage, collision tests, fail closed |
| Private code reaches browser/provider/log | Projection allowlists, egress consent, redaction/secret gates, service env isolation, canary-secret E2E |
| Model fabricates test/scan/advisory proof | Deterministic tools and authoritative sources override model/critic; unsupported claims fail |
| SLM adapter regresses or mismatches base | Exact hashes, held-out comparison, subgroup gates, three stable runs, atomic promotion and rollback |
| GPU/model/scanner unavailable | Lane-specific readiness, admission control, honest escalation/fallback, no false clean claim |
| Webhook/control-plane/network outage | Durable queue/DLQ, lease rules, ordered outbox, cursor replay/snapshot, labelled degraded mode |
| Frontend freeze blocks authorization/onboarding | Use a safe GitHub-native/admin path or obtain an explicit minimal frontend scope decision |
| Schema drift between owner lanes | Canonical owner, schema versioning, golden fixtures, generated checks, all-consumer merge gate |
| Scanner false positive or unpublished finding leak | Separate severity/confidence/reachability, restricted review, private report, no public default |
| Training data license/privacy/leakage issue | Provenance/license/reviewer/consent, split/dedupe/redaction gates, no automatic trace ingestion |
| Costs or latency exceed claims | Actual telemetry, fixed benchmark hardware/config, budgets, honest miss reporting, consented fallback |
| README/demo claims outrun implementation | Current-truth status, reachable surfaces only, evidence URLs/IDs required for every live claim |
| Backup restores deleted data improperly | Retention-aware backup policy, deletion receipts, restore tests, legal-hold rules |

## Hard release rules

- Do not enable `live` while any P0 item affecting that path is open.
- Do not waive a failing build, test, security scan, contract check, secret scan, or eval hard gate.
- Do not promote an adapter without exact files/hashes, reviewed data, frozen evaluation, three stable
  runs, loader proof, atomic activation, and rollback.
- Do not claim a task complete without its persisted real result URL or authenticated private-report
  URL.
- Do not treat fixture, dry-run, replay, local patch, generated output, or model confidence as live
  evidence.
- Do not execute commands copied from prompts/issues, scan external targets, publish vulnerabilities,
  expose a discovered secret, force-push, delete branches, publish releases/advisories, or mutate
  repository settings.
- Do not put GitHub/provider/server credentials in the runtime, gateway, browser, `NEXT_PUBLIC_*`, Git,
  fixtures, screenshots, evidence, URLs, or logs.
- Do not modify the frozen frontend presentation without a separate explicit scope decision.
- Do not expand supported modes, actions, languages, scanners, models, providers, or autonomy without
  contracts, policy, threat review, tests/evals, documentation, SLO, and rollback.

## Final definition of a proper product

Hermes/Helios may be called a proper supported product for its declared release tier only when all of
the following are true:

- [ ] Product scope, supported matrix, ownership, user roles, deployment model, data policy, provider
  policy, licensing, support, and known limitations are explicit.
- [ ] An authenticated authorized operator can install, onboard, preflight, dry-run, activate, inspect,
  pause, recover, rotate, revoke, and uninstall an allowlisted repository.
- [ ] The head orchestrator sees and safely uses the effective agent reservoir, including constrained
  spawn, exact model/adapter state, readiness, critic independence, and rollback.
- [ ] Planner/scheduler/execution/resume/outbox behavior is bounded, isolated, deterministic where
  required, and safe under crash, outage, timeout, pause, lease loss, and malformed model output.
- [ ] Every external effect is bound to an exact reviewed artifact and current policy/lease/control,
  executes exactly once, reconciles partial success, and stores a validated result URL.
- [ ] Maintainer, builder, and security modes each complete their declared real acceptance scenarios;
  read-only security work proves zero mutation and remediation is separately authorized.
- [ ] Models/tools/scanners are exact, ready, observable, licensed, and honest about failure/fallback.
  Every promoted SLM has governed data, reproducible training, objective held-out evidence, atomic
  activation, and demonstrated rollback.
- [ ] Convex remains canonical; storage, memory, events, findings, providers, and write-back are tenant/
  repository isolated, redacted, retained, exported, and deleted according to policy.
- [ ] The deployed client connects through authenticated scoped WSS, receives ordered resumable
  projections, displays honest token/cost/model/result data, and never becomes canonical truth.
- [ ] Clean-clone CI, cross-language contracts, security gates, all three eval suites, E2E failure
  matrix, performance/soak, backup/restore, rotation, rollback, and incident drills pass.
- [ ] Evidence contains real IDs, hashes, versions, timestamps, metrics, and result URLs; fixtures are
  labelled; three final identical runs and two timed rehearsals are retained.
- [ ] Security, privacy, legal, acceptable-use, disclosure, support, status, incident, retention,
  deletion, and release documentation match the behavior operators actually receive.

Until this checklist is satisfied for a specific release tier, describe the system as an in-progress
prototype or controlled pilot and list the remaining gates plainly.
