# Team Member 3 — LoRA/QLoRA, Evaluation, Realtime Integration, Reliability, and Evidence

## Mission

Own model quality and whole-system proof. The frontend is already built, so your work is not to design
screens or recreate a dashboard. You replace that old assignment with five substantial engineering
responsibilities:

1. build a governed LoRA/QLoRA data and training pipeline;
2. own the multi-mode Gauntlet, scorers, regression gates and model benchmarks;
3. build the backend WebSocket compatibility gateway used by the completed Next.js client;
4. run cross-system reliability, privacy, security and performance acceptance tests; and
5. produce honest documentation, evidence and rehearsal assets for the live demo.

Your output proves that Hermes can be used as a GitHub maintainer, product-building agency, and
repository vulnerability auditor while retaining one safe, observable Helios execution model.

The judged headline remains the maintainer-on-duty workflow from `soul.md`. Builder and security modes
are real reusable capabilities, not a vague “future use” slide: each needs fixtures, an end-to-end run,
objective evaluation, and an evidence artifact.

## Planning baseline — 12 July 2026

- The existing root Next.js/React frontend under `src/` and `public/` is complete and frozen for this
  split. Do not add pages, components, styles, responsive work, route trees, UI kits or a replacement
  dashboard.
- Do not create the obsolete `apps/dashboard` Vite application from the old assignment.
- You may build a **backend compatibility gateway**, automated browser/E2E tests, documentation and
  packaging. Those are integration/quality tasks, not frontend construction.
- The current repository uses Bun and Next.js. Preserve `bun.lock`; do not introduce pnpm workspace
  assumptions or commit a generated `package-lock.json`.
- `soul.md` is authoritative for Hermes as the agency and Helios as the runtime, real GitHub results,
  independent critic, typed handoffs, observable costs, memory, policy and hard guardrails.
- “Frontend Expert” is a runtime specialist that repairs web repositories. It remains in the expert
  roster even though the Hermes frontend itself is complete.

## Equal three-person split

| Member | Primary lane | Your dependency on them |
|---|---|---|
| **1 — Runtime** | Planner, scheduler, experts, model serving, tools, critic | Loads promoted adapters; executes eval tasks; emits canonical events |
| **2 — Control plane** | Convex, contracts, GitHub/Cloudflare, policy, memory, secrets | Persists evals/promotions; exposes canonical cursor feed; commits approved cases |
| **3 — You** | Training, evaluation, gateway, E2E reliability, evidence | Produce adapter/eval packages and prove the merged system |

Every member has a 36-hour schedule with roughly 30 owned engineering hours and 6 shared integration
hours. This is not a “docs-only” lane: training, scoring and gateway code are production dependencies.

## Repository ownership

You own:

```text
training/
├─ pyproject.toml
├─ configs/
├─ src/hermes_training/
└─ tests/
datasets/
├─ manifests/
├─ processed/                 # small reviewed data only; respect licenses/privacy
└─ README.md
evals/
├─ gauntlet/
├─ scorers/
├─ snapshots/
└─ reports/
adapters/
├─ manifests/                 # metadata/checksums/model cards; large weights are ignored
├─ promoted/
└─ README.md
benchmarks/
gateway/
├─ src/
├─ tests/
└─ README.md
tests/e2e/
evidence/
docs/runbooks/
```

You do not own:

```text
src/components/, src/app/page.tsx, src/app/globals.css, public/ # completed frontend
runtime/, agents/                                                # Member 1
convex/, apps/worker/, packages/contracts/, policy/              # Member 2
src/app/api/                                                      # Member 2 server boundary
```

If a frozen frontend behavior blocks integration, document the exact payload and observed behavior.
Do not quietly edit UI code. The team can make a separate explicit scope decision; your assigned work
continues through fixtures and gateway contract tests.

## Product modes to train and evaluate

### Mode A — GitHub maintainer

Required capabilities:

- classify issue/PR work and apply repository-valid labels/priority;
- detect likely duplicates with evidence;
- ask for missing reproduction information;
- answer from code/docs/live research with citations;
- reproduce and fix small bugs with tests;
- review community PRs;
- update docs and draft releases;
- escalate security, ambiguity, protected paths and repeated critic rejection.

Primary quality targets come from `soul.md`: triage/response at or above 85%, fix at or above 70%,
three stable complete runs, and fast-lane latency under 60 seconds on the demo machine.

### Mode B — Product builder

Required capabilities:

- turn a brief into bounded requirements and acceptance criteria;
- choose an architecture consistent with repository constraints;
- decompose frontend/backend/test/security/docs work into a DAG;
- generate complete, reviewable files rather than disconnected snippets;
- compile/typecheck/test the result;
- produce a branch/PR and build manifest;
- explain tradeoffs and escalate missing credentials/product decisions.

The completed frontend already represents this product-builder experience. Your gateway lets backend
progress, code artifacts, costs and completion URLs reach it without treating UI state as truth.

### Mode C — Repository security/vulnerability audit

Required capabilities:

- inventory languages, packages, workflows, exposure points and trust boundaries;
- run approved dependency, secret, SAST and configuration checks;
- normalize and deduplicate findings;
- rank severity, confidence, exploitability and reachability using deterministic evidence;
- create an SBOM/SARIF-style artifact where supported;
- avoid leaking suspected secrets or unpublished vulnerabilities;
- propose a minimal fix and validate it with tests/rescan;
- produce a private report, draft advisory or separately approved remediation PR.

No evaluation may reward active exploitation, destructive tests, external target scanning, secret
exfiltration or public disclosure. Read-only local audit is the default.

## Realtime compatibility gateway

The existing client uses `NEXT_PUBLIC_ORCHESTRATOR_URL`, defaulting to `ws://localhost:9100`. Build a
small backend gateway at that boundary. Convex remains the source of truth; the gateway projects and
replays safe events.

### Frozen client messages to accept

The current client sends:

```json
{"type":"prompt","data":"Build or maintain this repository..."}
```

It may also send an envelope-shaped agent message:

```json
{
  "type": "EVENT",
  "src": "ui-observer",
  "dst": "pm",
  "ts": 1780000000000,
  "payload": {"kind": "CHAT_MESSAGE", "text": "..."}
}
```

Validate size, type, origin and rate. Convert accepted prompts into Member 2's canonical task draft,
infer no dangerous permission, and require repository/mode/action confirmation through policy before
live execution. Duplicate client messages must not create duplicate tasks.

### Frozen client messages to emit

Support the direct event shapes the current Zustand store already consumes:

```text
progress      { type, data }
terminal      { type, data }
file          { type, data:{filename,language,path} }
token_usage   { type, data:{office,input_tokens,output_tokens,cost_usd,latency_s} }
cost_update   { type, data }
complete      { type, data, githubUrl?, projectName?, files? }
error         { type, data }
```

Also support a versioned canonical envelope for tests and later clients:

```text
schemaVersion, eventId, type, src, dst, ts, sequence,
taskId?, runId?, spanId?, payload, redactionLevel
```

Map structured agent/status fields to display text at the last projection step. Do not parse business
state back out of prose or emojis.

### Gateway behavior

- Authenticate task-creating connections; allow an unauthenticated read-only demo stream only if
  explicitly enabled and fully redacted.
- Subscribe to Member 2's canonical cursor feed; never maintain an independent task/run database.
- Keep a bounded in-memory connection buffer only; persist cursors through the control plane.
- Include event ID and monotonic run sequence; dedupe repeats.
- Reconnect upstream with exponential backoff/jitter; replay from `lastEventId` or request a snapshot.
- Never replay mutation commands automatically after an ambiguous disconnect.
- Send heartbeat and server time; close stale/oversized/rate-abusive clients.
- Mark fixture, dry-run, degraded, replayed and live data explicitly.
- Keep actual local/remote cost separate from cloud-equivalent cost.
- Preserve adapter/base-model identity in terminal/diagnostic projections.
- Emit completion only after Member 2 persists a terminal result URL; fixture runs never count.

### Wrapper/status compatibility

Expose a safe `/status` snapshot with wrapper ID/type/status/last-seen metadata and status values
`IDLE`, `THINKING`, `WORKING`, `BLOCKED`. The current client contains inactive registration/status
code; test the gateway endpoint and document the frozen-client limitation instead of claiming the
canvas is live when it is not consuming that path.

## LoRA/QLoRA strategy

### What is being fine-tuned

Use one high-value adapter first: the Qwen3-4B triage/reply/docs family. It has repeated, structured,
high-volume outputs and fits the fast lane. Do not spend the first training window on the Planner,
Critic or code model.

- Keep Planner base-first so it generalizes across all three modes.
- Keep Critic independent and never attach the same adapter that produced the output it judges.
- Add a security-classification adapter only after the maintainer adapter passes and there is enough
  reviewed security data.
- Use prompts/RAG/policy for current repository facts, tools and safety. Fine-tuning is for behavior,
  structure, tone and stable classification—not changing permissions or memorizing current facts.

### QLoRA versus LoRA

- Use QLoRA by default when GPU memory is constrained: load the trainable base through 4-bit
  bitsandbytes and train standard PEFT LoRA weights.
- Use ordinary BF16/FP16 LoRA only if the base model fits with safe headroom and is measurably faster or
  more stable on the available machine.
- Do not train from a GGUF file. Obtain the exact original Hugging Face base revision/tokenizer that
  corresponds to the GGUF used by llama.cpp.
- Export the selected PEFT adapter to a llama.cpp-compatible GGUF LoRA adapter, then load it separately
  from the exact GGUF base. Do not merge it into the only copy of the base model.

Official implementation references:

- [TRL PEFT integration](https://huggingface.co/docs/trl/main/en/peft_integration)
- [PEFT LoRA configuration](https://huggingface.co/docs/peft/main/package_reference/lora)
- [Transformers bitsandbytes/QLoRA guidance](https://huggingface.co/docs/transformers/quantization/bitsandbytes)
- [llama.cpp LoRA/GGUF support](https://github.com/ggml-org/llama.cpp)

### Starting training configuration

Treat these as the first reproducible sweep, not magic constants:

```text
method: QLoRA SFT
quantization: 4-bit NF4
compute dtype: BF16 when supported, otherwise FP16
double quantization: enabled for the QLoRA candidate
target modules: all-linear candidate plus a narrower attention/MLP candidate
rank: 16 and 32
alpha: 32 and 64
dropout: 0.05
epochs: 1–3 with early stopping
learning rate: small logged sweep; no manual untracked retuning
packing: compare on/off for short examples
seed: at least 3 evaluation seeds for the selected candidate
```

Log exact library versions, CUDA/backend, GPU, seed, sequence length, batch/accumulation, optimizer,
scheduler, steps, checkpoints, peak VRAM, wall time and energy/cost estimate.

## Dataset governance

### Allowed sources

- reviewed public issues, PRs, maintainer replies and patches from allowlisted/licensed repositories;
- team's own repository history and genuine corrections;
- synthetic edge cases generated from schemas, then manually reviewed;
- approved `pending-review` failures only after a human supplies the correct target;
- public vulnerability fixtures designed for defensive testing.

### Forbidden sources

- secrets, tokens, private keys, raw secret findings or private issue content without explicit consent;
- judge/live-demo inputs before evaluation;
- held-out Gauntlet cases or their goldens;
- unreviewed model-generated answers treated as truth;
- code/text whose license or provenance is unknown;
- exploit payloads intended for unauthorized systems.

### Dataset record

Each normalized JSONL record contains:

```text
exampleId, mode, taskType, repositoryGroup, sourceUrl?, sourceCommit?,
license, provenance, collectedAt, reviewer, reviewStatus,
input, expectedArtifactType, target, policyContext,
safetyTags[], piiSecretScan, split, contentSha256
```

Redact identities not needed for the task. Store author login only when entity-memory behavior is the
explicit evaluated feature and consent/policy allows it.

### Split rules

- Split by repository and issue/PR thread, never random message rows from the same conversation.
- Keep a time-later test slice when history permits.
- Freeze train/dev/test manifests with hashes before training.
- Keep the entire final Gauntlet held out from all optimization, prompt selection and adapter training.
- Deduplicate near-identical code/text across splits using normalized hashes plus similarity review.
- Report per-mode, repository, language, severity and safety subgroup counts.

## Training pipeline layout and commands

Create:

```text
training/src/hermes_training/
├─ prepare.py
├─ redact.py
├─ dedupe.py
├─ split.py
├─ validate.py
├─ format_sft.py
├─ train.py
├─ sweep.py
├─ export_peft.py
├─ convert_gguf.py
├─ model_card.py
└─ manifest.py
```

Required commands:

```bash
python -m hermes_training.prepare --config training/configs/triage.yaml
python -m hermes_training.validate --manifest datasets/manifests/triage-v1.json
python -m hermes_training.train --config training/configs/triage-qlora.yaml
python -m hermes_training.export_peft --run <training-run-id>
python -m hermes_training.convert_gguf --adapter <adapter-dir>
python -m hermes_training.model_card --run <training-run-id>
```

Every output directory contains config, environment lock, dataset manifest hash, checkpoints, metrics,
PEFT adapter, GGUF adapter when conversion succeeds, SHA-256 checksums and model card. Large weights are
gitignored and stored in an approved local/artifact location; manifests remain in Git.

## Adapter promotion contract

Supply Member 1 and Member 2:

```text
adapterId, adapterVersion, adapterSha256, format,
baseModelId, baseModelRevision, baseModelSha256, tokenizerSha256,
targetRoles[], trainingRunId, datasetManifestSha256,
lora{rank,alpha,dropout,targetModules}, quantization,
trainMetrics, heldOutEvalReportSha256, benchmarkReportSha256,
knownLimitations, rollbackTo, promotedBy, promotedAt
```

Promotion rules:

1. exact base/tokenizer compatibility passes;
2. adapter beats the frozen base on its primary metric by the declared meaningful margin;
3. no hard safety, secret-leak, policy-following or critical subgroup regression;
4. all existing maintainer thresholds still pass;
5. fast lane remains under 60 seconds and memory fits the demo machine;
6. three stable full evaluation runs pass for the final configuration;
7. Member 1 loader smoke test and Member 2 atomic promotion test pass;
8. rollback is demonstrated before live use.

If the adapter fails, document it as an experiment and ship the base model. “We trained LoRA” is not a
reason to deploy a regression.

## Multi-mode Gauntlet

You own cases, scorers, reports and threshold logic. Member 1 supplies execution hooks; Member 2 stores
results and runs the blocking CI workflow.

### Maintainer suite — minimum 40 core cases

- 25 triage/dedupe cases: exact class, allowed label set, priority, duplicate link/threshold;
- 8 response/clarification/docs cases: hard assertions plus held-out rubric;
- 7 fix/repro cases: frozen repository snapshot and objective pre/post tests.

### Builder suite — minimum 15 cases

- 5 requirement/architecture cases with constraint and acceptance-criterion coverage;
- 7 implementation cases across at least two languages/stacks, scored by compile/typecheck/tests;
- 3 integration/package cases covering multi-file consistency, docs and build manifest.

Score builder output by objective checks first: applies cleanly, builds, tests, meets requested behavior,
contains no secret, stays within scope and supplies required artifacts. An LLM rubric may grade clarity
or architecture only after hard checks pass.

### Security suite — minimum 20 cases

- known vulnerable dependencies with fixed advisory goldens;
- true and false secret fixtures where raw values must never appear in reports;
- SAST/configuration fixtures with known findings and deliberate false positives;
- reachability/severity distinctions;
- remediation cases where the fix must pass tests and rescan;
- authorization fixtures proving the system refuses external/destructive scanning.

Track precision, recall and F1 by severity/category, false-positive rate, secret-leak count, remediation
success and unsupported-CVE-claim count. Any secret leak or unauthorized action is an automatic gate
failure regardless of aggregate score.

### Regression reports

For every candidate compare on identical frozen cases:

```text
base model + v1 prompt
base model + improved prompt/persona
base model + LoRA/QLoRA candidate
final selected model/prompt/adapter configuration
```

Report pass rate, per-mode/subgroup metrics, schema-valid rate, critic revise/escalation rate, token
counts, latency, peak RAM/VRAM, cold/warm behavior and actual/provider cost. Keep seeds and case-set
version identical across the comparison.

Use the version story:

- `agents-v1`: honest base/prompt baseline;
- `agents-v2`: prompt/persona improvement;
- `agents-v3`: QLoRA/LoRA candidate;
- `agents-v4`: best validated configuration, which may be base-only if the adapter loses.

## Closed-loop curation

Member 2 captures failures, escalations and human corrections as `pending-review`. You:

1. reproduce the failure against the frozen input/version;
2. redact private/secret content;
3. decide whether it is a product bug, policy bug, prompt bug, data candidate or eval-only edge case;
4. obtain a human-authored/corroborated target;
5. add it to a reviewed dataset or eval manifest—but never both sides of the same held-out comparison;
6. record provenance, reviewer and rationale;
7. send approved eval cases to Member 2 for audited Git commit.

No automatic trace-to-training path is allowed. Model self-output is never silently used as a label.

## Reliability and end-to-end acceptance

Build deterministic fake runtime/control-plane streams first, then run the same suites against the live
merged services.

### Failure matrix

Test:

- malformed planner JSON and visible fallback;
- model cold start, timeout, crash, adapter mismatch and base rollback;
- duplicate/out-of-order/missing realtime events and cursor resync;
- WebSocket disconnect during a task and reconnect without duplicate task creation;
- Convex outage, outbox replay and expired lease;
- GitHub rate limit, webhook replay, base-SHA conflict and partial write-back failure;
- failed build/test/security scan and critic disagreement;
- private/local-only task attempting cloud egress;
- Linkup, Workers AI, Haiku and ElevenLabs outage;
- secret finding, unsafe report text, attempted public disclosure and unauthorized scan;
- global pause/emergency stop during concurrent work.

### Performance matrix

- ten consecutive warmed maintainer fast-lane runs;
- cold and warm base-vs-adapter runs;
- gateway event latency, reconnect/replay time and memory under a multi-run stream;
- build mode on one small full-stack fixture;
- security audit on at least two repositories/language ecosystems;
- no training job competing with demo inference during evidence collection.

### Frontend regression-only checks

Without changing frontend code, verify the existing client can:

- send a prompt and receive progress;
- show agent/system messages and terminal output;
- receive file/code artifacts where its current store supports them;
- show token/cost events without fabricated values;
- show the final GitHub/project URL;
- reconnect without duplicating a task.

Do not claim unimplemented `soul.md` management surfaces as complete evidence. Record any frozen-client
gap honestly in the release checklist so the pitch and screenshots match the product that exists.

## Evidence and documentation

Maintain:

```text
evidence/
├─ README.md
├─ run-ids.md
├─ urls.md
├─ screenshots/
├─ recordings/
├─ evals/
├─ adapters/
├─ security/
├─ builds/
├─ alerts/
├─ power-ups/
└─ rehearsal-log.md
```

Evidence required:

- real judge-authored maintainer task and real GitHub result URL;
- green fix PR, critic revise→pass, spawn and escalation runs;
- different plan DAGs for maintain/build/security modes;
- one tested builder PR and build/test manifest;
- one defensive vulnerability report plus separately approved remediation PR;
- v1→v4 eval report and three stable final runs;
- base-vs-LoRA report, adapter manifest/model card and rollback recording;
- one honest alert, memory-aware interaction and policy effect;
- actual Convex/Cloudflare/Linkup/ElevenLabs/Wispr proof where used;
- latency/cost reports that distinguish local actual cost from cloud-equivalent cost.

Every evidence folder README names the task/run IDs, real URLs, capture time, commit SHA, versions and
what the proof demonstrates. Label fixtures and rehearsals. Never present them as real completions.

Write operator/developer runbooks for:

- starting Bun frontend plus all backend services;
- configuring local models and promoted adapters;
- maintainer, builder and security-audit mode usage;
- repository consent/allowlist and data-egress controls;
- interpreting a finding and creating a remediation PR;
- running fast/full evals and reproducing reports;
- adapter promotion/rollback;
- emergency pause, offline fallback and demo recovery.

## 36-hour execution plan

| Hours | Owned outcome |
|---|---|
| 0–4 | Quality repo skeleton, eval/task schemas, hardware/base-model audit, dataset governance, gateway protocol/fixture server |
| 4–10 | Gateway prompt/event/reconnect path, `agents-v1` baseline, first maintainer cases, data ingest/redact/dedupe/split pipeline |
| 10–18 | 40-case maintainer Gauntlet, builder/security suites, deterministic scorers, QLoRA smoke and full candidate run |
| 18–26 | PEFT/GGUF export, model card/manifest, base-vs-adapter benchmarks, gateway live control-plane integration, failure matrix |
| 26–30 | v2/v3/v4 comparisons, three final full runs, E2E/privacy/security/performance acceptance, promotion/rollback proof |
| 30–34 | Shared integration across all three modes, real URLs/run IDs, documentation and evidence capture, blocker fixes |
| 34–36 | Two timed rehearsals, fallback replay, frozen evidence index and demo/evaluation operations |

## Required automated tests

### Data and training

- provenance/license/reviewer fields are mandatory;
- secret/PII scanner blocks unsafe records;
- split leakage and near-duplicate checks fail the pipeline;
- training is reproducible from config/manifest/seed;
- manifests and adapter outputs have verified hashes;
- GGUF conversion/load smoke test uses the exact declared base.

### Evaluation

- scorers are deterministic on fixed fixtures and return nonzero below thresholds;
- hard build/test/security failures cannot be overridden by an LLM score;
- Gauntlet is absent from training manifests;
- base and adapter use identical case sets/seeds;
- safety subgroup regressions and secret leaks block promotion;
- reports preserve actual/equivalent cost and local/remote distinctions.

### Gateway

- invalid/oversized/rate-abusive messages are rejected;
- duplicate prompt IDs enqueue once;
- event sequence gaps trigger replay/snapshot;
- reconnect does not replay a mutation;
- redaction prevents secrets/private fields in client messages;
- fixture/dry-run events cannot become real-completion counters;
- completion requires a persisted result URL.

### End-to-end modes

- maintainer issue becomes a useful reply/labels and one result URL;
- builder brief becomes requirements, code, tests, security report and PR;
- security audit produces normalized redacted findings and no mutation in read-only mode;
- approved remediation produces a tested PR and rescan result;
- global pause, lost lease, base conflict and provider outage degrade safely.

## Definition of done

- Training/data pipeline is reproducible, governed, split-safe and free of committed large weights.
- One QLoRA/LoRA candidate is trained, exported, model-carded and honestly compared to the base.
- Promotion happens only if quality/safety/latency gates pass; rollback is demonstrated.
- Critic stays independent and no adapter changes tools, policy or hard safety.
- Maintainer, builder and security Gauntlets run locally and through Member 2's CI gate.
- Gateway maps canonical events to the frozen client, handles reconnect/replay and never becomes truth.
- The merged system completes one real acceptance run in each mode.
- Security reports redact secrets, avoid unsupported claims and require separate consent for remediation.
- Evidence contains real IDs, URLs, versions, manifests, reports and timestamps—no fabricated proof.
- Two rehearsals complete with training stopped, models warm, fallbacks ready and navigation/demo order
  frozen.

## Merge and handoff checklist

1. Work on `member3/model-quality`; do not edit completed frontend presentation code.
2. Freeze eval/event/adapter schemas with Members 1 and 2 at hour 4.
3. Publish gateway fixtures and baseline report by hour 10.
4. Publish candidate adapter + manifest + model card by hour 18–22; never pass an unverified path/hash.
5. Member 1 must pass loader/telemetry/rollback tests before promotion.
6. Member 2 must pass registry/CI/atomic pointer tests before promotion.
7. Integrate at hours 10, 18, 26 and 30; do not force-push consumed reports/manifests.
8. Any final model, prompt, policy, adapter, dataset or case-set change invalidates the three evidence
   runs and requires rerunning them.
9. Before final merge run training tests, full Gauntlet, gateway tests, E2E suites, Bun build/lint and
   the two rehearsal scenarios.
10. Hand the team one evidence index with exact links plus one fallback replay; do not rely on memory
    during judging.
