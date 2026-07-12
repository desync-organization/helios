# SOUL.md — Hermes

**The Autonomous Maintainer Agency, powered by the Helios Runtime**

> Helios is the operating system. Hermes is the agency that runs on it.
> Helios manages models the way an OS manages processes. Hermes replaces a human function:
> the open-source maintainer-on-duty.

- **Version:** 1.0 (hackathon build)
- **Track:** AI as Agency
- **Target score:** L5 on all seven parameters (164 base) + all five power-ups (+125) + uncapped overflow (+20/task completed live)
- **One sentence:** A manager agent plans, a swarm of on-device Small Language Model specialists executes, work lands on a **real GitHub repository** — issues triaged, duplicates closed, bugs fixed with tested PRs, docs updated, releases drafted — autonomously, under 60 seconds and under $0.01 per task, with a control surface a non-engineer can operate.
- **Capability envelope:** The same Helios kernel also turns scoped briefs into tested build PRs and
  performs consented, defensive repository vulnerability audits; the maintainer-on-duty flow remains
  the primary declared job and judging story.

---

## Table of Contents

1. [Why this exact framing wins](#1-why-this-exact-framing-wins)
2. [Use-case analysis — every candidate, scored against the rubric](#2-use-case-analysis)
3. [The declared job](#3-the-declared-job)
4. [System architecture](#4-system-architecture)
5. [Agent org structure → L5](#5-agent-org-structure--l5)
6. [Working product & real surfaces → L5 + overflow farming](#6-working-product--real-surfaces--l5)
7. [Handoffs & memory → L5](#7-handoffs--memory--l5)
8. [Observability → L5](#8-observability--l5)
9. [Evaluation & iteration → L5](#9-evaluation--iteration--l5)
10. [Cost & latency → L5](#10-cost--latency--l5)
11. [Management UI → L5](#11-management-ui--l5)
12. [Power-ups — all five, with evidence plans](#12-power-ups)
13. [Technology stack (final)](#13-technology-stack)
14. [Data model](#14-data-model)
15. [Autonomy & guardrail policy](#15-autonomy--guardrail-policy)
16. [Demo runbook — minute by minute](#16-demo-runbook)
17. [Build plan & task split](#17-build-plan)
18. [Risk register & fallbacks](#18-risk-register)
19. [Scoring math](#19-scoring-math)
20. [Definition of Done — the L5 checklist](#20-definition-of-done)

---

## 1. Why this exact framing wins

The original Helios PRD describes an on-device AI coding copilot. That is a **tool**. This rubric
does not score tools. It scores **agencies**: a team of agents that replaces a full human
function, produces real output on real surfaces, and can be operated by a non-engineer.

Three facts about the rubric dictate the strategy:

1. **"Real repo" is explicitly listed as an L5 real live surface.** The rubric's own L5 example
   list for Working Product reads: *"live site, real ATS, real support queue, real repo."*
   Every other team doing hiring or support has to fake an ATS or a customer queue (capped at
   L3, "staged surfaces"). We operate on GitHub — a surface that is real by construction,
   public, verifiable, and where **judges themselves can create real work items live** by
   filing an issue.

2. **Overflow points are uncapped: +20 per additional real task completed autonomously during
   judging.** The winning demo is not one impressive task — it is a *stream* of small real
   tasks. Issue triage is the perfect overflow unit: high volume, fast, real, verifiable.

3. **Cost/latency L5 requires BOTH under 1 minute AND under $0.10.** On-device SLM inference has
   a marginal cost of $0.00 per task. No cloud-API team can beat that number. Our trace shows
   `$0.000` next to every local step. This turns Helios's original soul — on-device execution —
   from a philosophical preference into a **rubric weapon**.

The pivot, in one line: **don't demo a copilot that helps a developer; demo an agency that
replaced the developer's on-call maintainer shift.**

Naming: **Helios** is the runtime (planner, scheduler, model manager, workspace, experts —
everything from the PRD survives intact). **Hermes** is the product: the maintainer agency
built on Helios, named for the messenger god who handles everything inbound. The repo is
`Hermes`. Judges get one clean story: "we built an AI operating system, and the first company
running on it is a software maintenance agency."

---

## 2. Use-case analysis

Every candidate function was scored against the six rubric dimensions that vary by use case.
✅ = naturally L5-capable, ⚠️ = achievable with effort, ❌ = structurally capped.

### Candidate A — OSS Maintainer Agency (GitHub) — **CHOSEN**

| Dimension | Verdict | Why |
|---|---|---|
| Real surface | ✅ | GitHub is real by definition; rubric names "real repo" as L5. Judges can file real issues live. |
| Task volume for overflow | ✅ | Triage tasks are 30–60s each; can complete dozens during judging. |
| Cost/latency L5 | ✅ | Triage lane fits <60s; local inference is $0. |
| Memory story | ✅ | Contributor history, repo conventions, CONTRIBUTING.md as policy layer — all natural. |
| Eval story | ✅ | Historical issues with known outcomes = free golden dataset. |
| Non-eng operator story | ✅ | "Community manager runs the maintainer bot" is plausible; Role Builder demo works. |

### Candidate B — Support Desk Agency (tickets/refunds)

| Dimension | Verdict | Why |
|---|---|---|
| Real surface | ❌ | No real customers → sandbox Zendesk/Gmail → **L3 cap** ("staged surfaces… this is the ceiling"). |
| Everything else | ⚠️ | Fine, but the L3 root-parameter cap costs 32+ points on the 20x parameter alone. |

### Candidate C — Hiring Agency (screen candidates, update ATS)

| Dimension | Verdict | Why |
|---|---|---|
| Real surface | ❌ | No real candidates or real ATS tenant during a hackathon → dummy ATS → **L3 cap**. |
| Ethics/optics | ⚠️ | Auto-rejecting (fake) humans without review reads badly to judges. |

### Candidate D — Quick-commerce Ops (orders, refunds, dispatch)

| Dimension | Verdict | Why |
|---|---|---|
| Real surface | ❌ | No access to a real order system → mocked DB → **L3 cap**. |

### Candidate E — Marketing/Content Agency (publish to a live site)

| Dimension | Verdict | Why |
|---|---|---|
| Real surface | ✅ | A live Cloudflare Pages site is real. |
| Task success measurability | ⚠️ | "Good copy" is subjective; 85% success across repeated runs is hard to *prove* to a mentor. |
| Overflow volume | ⚠️ | Publishing 15 pages during judging looks like spam, not work. |
| Verdict | Runner-up. We keep a slice of it: Hermes maintains the project's own live docs site on Cloudflare Pages — a second real surface for free. |

### Why A dominates

The Working Product parameter is weighted **20x (max 80)** — more than the next two parameters
combined. Any use case that cannot escape staged surfaces is capped at L3 there, losing ~32
points before the demo even starts, and earns zero overflow. GitHub is the only surface a
student team can access that is simultaneously: real, live, public, high-volume,
machine-verifiable, and safe to let agents write to.

**Bonus:** Hermes maintains **its own repository**. The agency that fixes its own bugs is a
story judges retell. Dogfooding also generates authentic issue traffic before judging day.

### Secondary use cases (mention in pitch, don't build)

These prove the Helios runtime generalizes — one slide each, zero code:

- **Internal platform team**: Hermes triages Sentry/CI failures into fixed PRs.
- **Agency-for-hire**: one Helios install runs maintainer duty for N client repos (multi-tenant
  policy layer already supports this — policies are per-repo).
- **Docs agency**: keeps SDK docs in sync with code across releases.
- **Security response desk**: CVE intake → dependency audit → patch PR (Security expert exists
  in the registry already).

---

## 3. The declared job

> **Hermes replaces the "maintainer-on-duty" rotation of a software project.**

The human function being replaced, decomposed exactly as a staffing plan would be:

| Human duty | Hermes task type | Lane | Autonomous? |
|---|---|---|---|
| Read every new issue, understand it | `intake` | Fast | Yes |
| Classify: bug / feature / question / spam | `classify` | Fast | Yes |
| Detect duplicates, link & close | `dedupe` | Fast | Yes (close w/ link) |
| Ask for missing repro info | `clarify` | Fast | Yes |
| Label, prioritize, milestone | `label` | Fast | Yes |
| Answer questions from docs/code | `respond` | Fast | Yes |
| Reproduce reported bugs | `repro` | Deep | Yes |
| Fix small bugs, open tested PR | `fix` | Deep | Yes (merge gated by CI + policy) |
| Review inbound community PRs | `review` | Deep | Yes (comment); merge per policy |
| Keep docs in sync with changes | `docs` | Deep | Yes (docs-only merges autonomous) |
| Draft release notes | `release` | Deep | Yes (draft state) |
| Escalate the truly hard stuff | `escalate` | — | By exception, with full context |

**Fast lane** = completes in under 60 seconds, under $0.10 (actually $0.00 local). This is the
representative task for the cost/latency parameter and the overflow unit.
**Deep lane** = minutes-scale tasks (fix PRs). These are the "wow" overflow items — each merged
PR during judging is another +20.

**A task is "complete" when the artifact lands on GitHub**: a posted comment, an applied label,
a closed duplicate, a merged PR, a draft release. Nothing counts until it is visible on the
real surface. This is the internal bar for every feature below.

### 3.1 Multipurpose deployment profiles

The maintainer-on-duty job remains the primary declared job and judged vertical slice. Helios is a
general agency runtime, however, so the same planner, scheduler, expert registry, artifact workspace,
critic, policy engine and write-back boundary also ship with two additional profiles:

- **Builder (`build`)** — turns a scoped brief or feature request into requirements, architecture,
  a task DAG, code, tests, security checks, documentation and a reviewable GitHub PR.
- **Repository security auditor (`security_audit`)** — inventories an allowlisted repository, runs
  approved dependency/secret/SAST/config checks, normalizes and explains evidence, produces a private
  report, and can open a separately approved remediation PR.

These are profiles, not separate products or hard-coded orchestration paths. All three use typed
artifacts, least-privilege tools, independent critic review, repository policy, observable traces and
credential-free intents. Security audit is local/read-only by default: no external target scanning,
active exploitation, secret exfiltration or public disclosure is permitted. Builder deployment and
new-repository creation require explicit policy and human confirmation.

---

## 4. System architecture

Everything from the Helios PRD survives. What changes: the shared workspace and trace store
move to **Convex** (control plane, live-queryable), ingress moves to a **Cloudflare Worker**
(GitHub webhooks), and inference stays **on-device via llama.cpp** with Workers AI as fallback.

```
                       ┌─────────────────────────────────────────────┐
   GitHub (REAL)       │           CLOUD CONTROL PLANE               │
   issues/PRs/comments │                                             │
        │              │  Cloudflare Worker ──► Convex               │
        ▼              │  (webhook ingress,     (task queue, traces, │
   webhook ─────────────►  HMAC verify,          memory, evals,      │
        ▲              │   task enqueue)         alerts, live subs)  │
        │              │        ▲                    ▲   ▲           │
   write-backs         │        │                    │   │           │
        │              └────────┼────────────────────┼───┼───────────┘
        │                       │                    │   │
┌───────┴───────────────────────┴────────────────────┴───┴───────────┐
│                    ON-DEVICE: HELIOS RUNTIME                       │
│                                                                    │
│  Task Poller ──► PLANNER AGENT (manager)                           │
│                    │  reads task + memory pack + policy            │
│                    │  emits per-request Task Graph (DAG)           │
│                    ▼                                               │
│                 RUNTIME SCHEDULER                                  │
│                    │  topo-sort, parallel dispatch,                │
│                    │  retries, escalation routing                  │
│                    ▼                                               │
│                 MODEL MANAGER (llama.cpp servers)                  │
│                    │  pin hot models, LRU-evict cold,              │
│                    │  VRAM budget, load/unload events              │
│                    ▼                                               │
│   ┌──────────── EXPERT REGISTRY ─────────────────────────┐         │
│   │ triage  dedupe  python  frontend  test  docs         │         │
│   │ security  debug  research(Linkup)  critic  + SPAWNED │         │
│   └──────────────────────────┬───────────────────────────┘         │
│                              ▼                                     │
│                 SHARED WORKSPACE (artifacts, git worktree)         │
│                              ▼                                     │
│                 CRITIC GATE ──pass──► GitHub write-back            │
│                      │ fail: revision notes → scheduler            │
│                      │ blocked: escalation → human, full context   │
│                                                                    │
│  every step ──► trace event ──► Convex (tokens, cost, latency)     │
└────────────────────────────────────────────────────────────────────┘
        ▲                                          │
        │                                          ▼
   MANAGEMENT UI (React, Cloudflare Pages, Convex live queries)
   chat · run trace trees · diff view · alerts · Role Builder ·
   policy editor · eval dashboard · model/VRAM monitor
   + ElevenLabs voice (alerts out, work assignment in)
   + Wispr Flow (dictation into prompts/policies/replies)
```

### Component responsibilities

**Cloudflare Worker (ingress).** Receives GitHub webhooks (`issues`, `issue_comment`,
`pull_request`), verifies HMAC signature, normalizes into a `task` row in Convex. Also serves
the public status page. ~100 lines. This is what makes the system *react to the real world*
instead of being driven by a demo script.

**Convex (control plane).** Single source of truth for: task queue, run traces, all three
memory layers, eval sets and results, alert rules and firings, agent/role definitions (mirrored
from git), and the live subscriptions that make the dashboard update in real time with zero
polling code. Convex is the main backend — this is not a token integration.

**Task Poller (on-device).** Long-polls Convex for `pending` tasks, claims one atomically
(`claimTask` mutation with lease + heartbeat; lease expiry returns the task to the queue so a
crashed runtime never strands work), hands to Planner.

**Planner Agent (the manager).** The only agent that sees the whole task. Reads: task payload,
memory pack (§7), policy pack (§15). Emits a **typed plan**: JSON DAG of subtasks, each with
`expert`, `inputs` (artifact refs), `expected_artifact`, `acceptance_criteria`, `budget`
(tokens, seconds, tool permissions). The plan is itself an artifact — stored, traced, diffable.

**Runtime Scheduler.** Topological execution of the DAG. Independent branches run in parallel
(asyncio + multiple llama.cpp server slots). Handles: retries (1 retry with critic notes
attached), timeout kills, `BLOCKED` artifact routing (→ replan or escalate), budget
enforcement (kills any step that exceeds its token/second budget).

**Model Manager.** Each expert maps to a GGUF model + persona prompt (+ optional LoRA). Hot
set (planner, triage, embed) is **pinned in VRAM permanently** — this is the single most
important latency decision. Cold experts load on demand, LRU-evicted under a VRAM budget read
from `psutil`/`nvidia-smi`. Every load/unload is a trace event — the dashboard's model-timeline
view visualizes exactly the "OS for models" story.

**Shared Workspace.** A git worktree per deep-lane task + an artifact store. Agents never chat
with each other; they read and write **typed artifacts**: `plan`, `classification`,
`dup_report`, `repro_report`, `patch`, `test_result`, `review_notes`, `draft_reply`,
`blocked`, `escalation`. Artifact schemas are versioned JSON — this is what makes handoffs
lossless (§7) and traces diffable (§8).

**Critic Gate.** A separate model (never the one that produced the work) validates every
outbound artifact against the plan's acceptance criteria: does the patch apply, do tests pass,
does the reply actually answer the question, does the label match the classification rubric.
Three verdicts: `pass` → write-back; `revise` → back to scheduler with concrete notes (this
loop is the L4-org evidence, visible in every trace); `blocked` → escalation.

**Write-back layer.** The only component holding GitHub credentials. Executes: comment, label,
close, branch push, PR open, PR merge, release draft. Every write is idempotent (dedupe key =
`task_id + action`) and logged with the resulting GitHub URL — that URL is what a mentor
clicks to verify the task is real.

---

## 5. Agent org structure → L5

> L5 bar: *"Emergent org: manager spawns sub-specialists on the fly, agents escalate when
> stuck, roles self-adjust to task."* Mentor verification: *"a run where the trace shows a role
> that did not exist at kickoff."*

### 5.1 The baseline org (kickoff roster)

| Role | Model (default) | Job |
|---|---|---|
| **Planner** (manager) | Qwen3-8B Q4 (pinned) | Decompose, delegate, review, replan, escalate |
| Triage | Qwen3-4B Q4 (pinned) | Classify, prioritize, label |
| Dedupe | Embedding (bge-small) + Qwen3-4B | Similarity search over issue history, verdict |
| Python Expert | Qwen2.5-Coder-7B Q4 | Patches in Python code |
| Frontend Expert | Qwen2.5-Coder-7B Q4 (persona) | TS/React patches |
| Test Expert | Qwen2.5-Coder-7B Q4 (persona) | Write/run tests, report failures exactly |
| Docs Expert | Qwen3-4B | Docs sync, release notes, reply drafting |
| Debug Expert | Qwen2.5-Coder-7B | Repro scripts, stack-trace analysis |
| Security Expert | Qwen3-4B (persona) | Dependency/CVE checks, secret scanning on patches |
| Research Expert | Qwen3-4B + **Linkup** | Live web: error strings, changelogs, upstream issues |
| **Critic** | Qwen3-8B (shared weights with Planner, separate persona/context) | Gate everything outbound |

Personas sharing GGUF weights cost zero extra VRAM — an "expert" is
`(weights, system_prompt, tool_grants, LoRA?)`, so a 10-expert registry fits in ~3 loaded
models. This detail is worth saying out loud to mentors: it is the OS story (many processes,
few cores).

### 5.2 Dynamic planning (the L4 floor, guaranteed on every run)

The mentor test for L4: two structurally different requests produce different plans, and at
least one output gets bounced for revision.

- Plans are generated per-request, never from a routing table. A question-issue plans
  `intake → respond → critic` (3 nodes); a bug-with-stacktrace plans
  `intake → [dedupe ∥ repro] → fix → test → security → critic → write-back` (8 nodes, 2
  parallel). The dashboard renders both DAGs side by side — the visual difference *is* the
  mentor evidence.
- The Critic's `revise` verdict with concrete notes ("test asserts the old behavior; assert
  the fix per acceptance criterion 2") appears in traces routinely because the critic is
  strict by prompt design. We keep one known-good example bookmarked in the dashboard.

### 5.3 Emergent behaviors (the L5 evidence, engineered to be reproducible)

**Spawning.** The Planner has a `spawn_expert` tool:

```json
{"tool": "spawn_expert", "name": "rust-expert",
 "job": "Fix and review Rust code in this repository",
 "base_weights": "qwen2.5-coder-7b", "persona": "<generated>",
 "tools": ["read_file","write_file","run_cmd:cargo"],
 "budget": {"max_tokens": 8000, "max_seconds": 120}}
```

Trigger logic: when the plan needs a capability with no registry match above a similarity
threshold, the Planner composes a new role from base weights + generated persona + minimal
tool grants, registers it in Convex (`origin: "spawned", spawned_by: run_id`), and delegates.
The role persists — the org *grew*.

*Reproducible demo:* the maintained repo contains a small Rust utility crate and a `.sql`
migration dir; no Rust or SQL expert exists at kickoff. A seeded real issue ("cargo build
fails on the checksum util") forces a spawn, live. The trace tree shows `rust-expert` with a
birth timestamp mid-run, and the registry view shows `origin: spawned`. This is exactly the
mentor's verification sentence.

**Escalation with a concrete blocker.** Any expert can emit a `blocked` artifact — schema
requires `what_i_tried`, `exact_failure` (verbatim error), `smallest_failing_case`,
`what_i_need`. The Planner either replans around it (different expert, decomposed subtask) or
escalates to the human queue with the full artifact chain attached. **No agent ever fails
silently and no escalation ever restarts from zero** — the human picks up mid-context. The
Test Expert is prompted to escalate rather than loop after 2 failed attempts; loops die by
budget enforcement anyway.

**Role self-adjustment.** When the Critic bounces the same expert twice for the same class of
error, the Planner may patch the expert's persona (`adjust_role` tool: appends a constraint,
bumps the role's version in Convex). Trace shows role v1 → v2 with the diff. Small feature
(~50 lines), disproportionate rubric value: "roles self-adjust to task" verbatim.

---

## 6. Working product & real surfaces → L5

> L5 bar: *"End to end on real live surfaces, 85%+ success across 3+ repeated runs, escalates
> by exception only… production quality."* Overflow: *+1pt × 20 per additional real task
> completed autonomously during judging.*

### 6.1 The real surfaces (three of them)

1. **The Hermes repo itself** (`github.com/<team>/hermes`) — real code, real history, real CI.
   Hermes runs maintainer duty on its own repository from day 1 of the build. Every real bug
   we hit during the hackathon gets filed as a real issue and (where possible) handled by
   Hermes. By judging day the issue history is authentically real, not seeded theater.
2. **A second real repo the team already owns** (pick the team member repo with the most
   stars/issues) — proves multi-tenant: same install, different policy pack.
3. **The live docs site** (`hermes.<team>.pages.dev` on Cloudflare Pages) — the Docs expert's
   write-backs deploy here. A live site is the rubric's first-listed real surface.

**Staged-surface defense (this will be challenged):** the counter to "you made this repo for
the hackathon" is (a) repo #2 predates the event with organic history, (b) the Hermes repo's
issues are the team's genuine bugs with commit-linked fixes, and (c) **judges file the issues
during judging** — an issue authored live by a mentor on a public GitHub repo is real by any
definition. Lead with (c).

### 6.2 The 85% / 3-runs evidence

- Before judging: run the full gauntlet (§9) 3+ times end-to-end; the eval dashboard stores
  every run with pass rates ≥85% and links to the actual GitHub artifacts. This page is open
  in a tab when the mentor asks.
- During judging: the mentor files a fresh issue; stopwatch runs; the artifact lands. Repeat
  as many times as they'll allow.

### 6.3 Overflow farming (the uncapped score)

- **QR code on the demo table** → "File a real issue, watch an AI agency fix your bug." Every
  passerby-filed issue Hermes completes during judging = +20.
- A backlog of ~20 real unprocessed issues (accumulated organically, held un-triaged) released
  during judging → visible queue-drain on the dashboard, dozens of completed real tasks.
- 2–3 pre-scoped small real bugs (off-by-one, missing null check, doc typo — real ones we
  deliberately did not fix) for live deep-lane fix→test→PR→merge runs.

### 6.4 What "production quality" means here

Replies are written in maintainer voice (persona-tuned, no AI boilerplate, links to exact
files/lines), labels come from the repo's actual label taxonomy, PRs follow the repo's
CONTRIBUTING.md (branch naming, commit format, test requirements), and CI must be green before
any autonomous merge. A mentor reading the GitHub thread should not be able to tell where the
human maintainers stopped and Hermes started — that is the bar.

---

## 7. Handoffs & memory → L5

> L5 bar: *"Full relevant history and policy knowledge (now + this user's past + business
> rules), survives all handoffs."* The rubric names the three layers explicitly — we implement
> them by name so the mapping is impossible to miss.

### Layer 1 — NOW (working memory)

The task's artifact bundle in the shared workspace. Because agents communicate **only**
through typed artifacts, handoff loss is structurally impossible: the Test Expert receives the
`patch` artifact plus the full upstream chain (`plan`, `classification`, `repro_report`) by
reference. No agent ever re-asks for what a previous agent established — there is no chat to
lose.

### Layer 2 — THIS USER'S PAST (entity memory, in Convex)

- `entities/user/<github_login>`: every prior issue/PR/interaction, quality signals (do their
  repro steps usually work?), outcomes, prior escalations.
- `entities/issue/<n>`: full Hermes interaction history with that thread.
- `entities/repo/<name>`: conventions learned (test framework, review norms, module owners).

The Planner's context pack always includes the relevant entity snapshots. Demo moment: a
mentor files a second issue from the same GitHub account, and Hermes's reply references their
first one ("this looks related to #47 you filed earlier — that fix shipped in 0.3.1; can you
confirm you're on it?"). One retrieval call; enormous rubric optics.

### Layer 3 — WHAT THE BUSINESS ALLOWS (policy memory, in git)

`policy/` directory in the repo, version-controlled, hot-reloaded, editable from the
Management UI (edits commit through the write-back layer — the audit trail is git history):

- `triage.yaml` — label taxonomy, priority rubric, spam rules
- `autonomy.yaml` — what merges without a human (§15), spend/step budgets
- `escalation.yaml` — who gets what, with what context
- `voice.yaml` — reply tone, sign-off, language

Every plan node's acceptance criteria cite policy rules by id (`triage.priority.p1`), so
policy application is *visible in traces*, not claimed.

### Cross-task persistence

Task N's outcome updates entity memory in the same transaction as the trace write — nothing
"remembers to save later." Interrupted runs resume from the last completed DAG node (all state
is in Convex + workspace), so a mid-demo crash costs seconds, not the run.

---

## 8. Observability → L5

> L5 bar: *"diff two runs side by side, alerts on failure or cost spike, search across runs,
> senior eng would trust this to debug prod."*

### 8.1 Trace model

Every step emits one event to Convex, sub-100ms behind real time (live subscriptions — the
dashboard moves *while the run executes*, which is itself a demo moment):

```
span: { run_id, span_id, parent_span_id, agent, agent_version, model,
        prompt_hash, input_artifact_refs, output_artifact_ref,
        tokens_in, tokens_out, cost_usd, cost_cloud_equiv_usd,
        latency_ms, tool_calls[], verdict?, error? }
```

`cost_usd` is real spend (local = $0.000; Workers AI/Haiku fallback = actual). We *also* track
`cost_cloud_equiv_usd` (what the tokens would cost at Haiku pricing) — showing both is more
credible than a bare $0 and makes the on-device advantage quantitative.

### 8.2 Dashboard views (React + Convex live queries, hosted on Cloudflare Pages)

1. **Run list** — filter by task type, agent, status, repo, date; full-text search across
   prompts, artifacts, and errors (mentor: "find the run about the checksum bug" → typed, found).
2. **Trace tree** — who called whom, expandable spans, tokens/cost/latency per node, artifact
   inspection inline, plan-DAG overlay with live node status.
3. **Diff view** — two runs side by side, spans aligned by plan-node role, divergence
   highlighted: prompt diff, artifact diff, verdict diff. Pre-bookmarked pair: the failing and
   passing run of the same eval case across an agent version bump — one click answers the
   mentor's "explain a regression using the diff view."
4. **Cost/agent analytics** — spend and latency by agent, by task type, by hour. Answers
   "which agent spent the most this morning?" from the tool, in one filter.
5. **Model timeline** — VRAM occupancy and load/unload events over time (the Helios OS story,
   visualized).
6. **Alerts** — rules in Convex, evaluated by a Convex scheduled function: task failure,
   cost > 4× task-type baseline, latency > 2× baseline, escalation created, eval regression.
   Firings: dashboard banner + alert log + **ElevenLabs voice announcement** ("Run 4-1-2:
   cost anomaly, fix task at 4x baseline"). Keep one real firing in the log (trigger it
   honestly during rehearsal by feeding a pathological issue).

### 8.3 The mentor script we are ready for

- "Show me a run from an hour ago" → search, open, walk the tree.
- "Which agent is most expensive today?" → analytics filter.
- "Why did this run fail and this one pass?" → bookmarked diff.
- "Has an alert ever actually fired?" → alert log, real entry, timestamped.

---

## 9. Evaluation & iteration → L5

> L5 bar: *"failed runs feed a growing eval set, version-controlled prompts and agents,
> measurable gains across versions"* — plus L4's CI gate that actually blocks.

### 9.1 The Gauntlet (named eval set)

`evals/gauntlet/` in the repo — target ≥40 cases by judging, each a frozen real task:

- **Triage cases** (~25): real historical issues; golden = labels, classification, dup-link,
  priority. Scored exactly (set match).
- **Response cases** (~8): golden = rubric checklist; scored by LLM-judge (critic model,
  held-out prompt) + hard assertions (mentions the right file, no hallucinated version).
- **Fix cases** (~7): repo snapshot + issue; scored by *the repo's own test suite* passing
  post-patch — fully objective.

### 9.2 CI gate (the L4 floor)

Prompts, personas, plan templates, policies — all in `agents/` and `policy/` in git. Any PR
touching them triggers `eval.yml` (GitHub Actions): run the Gauntlet, **fail the check below
threshold** (triage ≥85%, fixes ≥70%). Branch protection makes the block real. During the
build we keep one genuinely blocked merge (a prompt "improvement" that tanked triage recall —
this will happen naturally; when it does, screenshot it, keep the PR unmerged as the exhibit).

### 9.3 The closed loop (the L5 differentiator)

Automatic, not aspirational — this is a Convex function, not a process document:

```
run fails critic / escalates / human corrects on GitHub
   → Convex `captureEvalCase` fires on the trace event
   → inputs + wrong output + corrected golden frozen as eval case (status: pending-review)
   → one-click approve in dashboard → committed to evals/gauntlet/ via write-back
   → next CI run includes it
```

Human corrections on GitHub (maintainer re-labels an issue Hermes labeled, edits its reply)
arrive via the same webhook ingress and auto-capture too — the real surface itself feeds the
eval set.

### 9.4 Measurable gains

Agent versions are git tags (`agents-v1`…`v4`). The eval dashboard charts Gauntlet pass rate
per version — a rising line with each version's tag and diff linked. Plan: tag v1 the moment
the pipeline first runs end-to-end (it will be mediocre — **that's good**, it's the base of
the climb), then v2/v3/v4 as prompts improve. The chart is only impressive if v1 is honest.

---

## 10. Cost & latency → L5

> L5 bar: *"Under 1 min AND under $0.10"*, both at once, on a representative real task, live,
> mentor holding the stopwatch.

### 10.1 The representative task

**Fast-lane triage-and-respond**: new real issue → classified, deduped, labeled, prioritized,
substantive reply posted on GitHub. This is not a trivial subset — it is the complete
front-desk unit of work as declared in §3, the same unit a human maintainer performs dozens of
times a week. Deep-lane fixes are declared as a separate task class (10.4).

### 10.2 Latency budget (target 40s, hard cap 55s)

| Step | Budget | How it holds |
|---|---|---|
| Webhook → task claimed | 3s | Worker + Convex push, poller at 1s interval |
| Planner plan | 6s | Qwen3-8B pinned, plan ≤300 tokens, JSON-schema-constrained decode |
| Triage ∥ Dedupe ∥ (Research) | 14s | parallel branches; embeddings pre-computed for all historical issues; classifier output ≤150 tokens |
| Reply draft | 12s | Qwen3-4B, context = artifacts only (no raw thread dump) |
| Critic | 6s | checklist verdict, ≤120 tokens |
| GitHub write-back | 3s | 2 REST calls |
| **Total** | **44s** | 16s slack vs the 60s bar |

Engineering rules that make this hold: hot models **never unload**; artifact discipline keeps
contexts small (the reply drafter reads a 40-line classification artifact, not a 3000-token
thread); all fast-lane outputs are schema-constrained (llama.cpp grammar) so no tokens are
wasted on prose; branches genuinely parallel across server slots.

### 10.3 Cost

Local inference: **$0.000 marginal**. Trace displays `$0.000 actual / $0.014 cloud-equiv` per
fast-lane run. If the Haiku-planner fallback (§18) is active, actual ≈ $0.004/run — still 25×
under the bar. Either way the stopwatch-and-trace moment reads: **~44 seconds, $0.00**.

### 10.4 Deep lane, declared honestly

Fix tasks: 3–8 min, $0.00 local. We declare both lanes on the scoring sheet; the fast lane is
the representative unit for this parameter (it is most of the job's volume, which we can show
from the run analytics), and mentors see deep-lane runs anyway as overflow. Honesty here
protects the 20x parameter's credibility.

### 10.5 Hardware

Demo machine: RTX 4060+ (8GB+ VRAM) or M-series Mac (16GB+). Pinned set ≈ 7.5GB
(8B-Q4 ≈ 5GB shared planner/critic + 4B-Q4 ≈ 2.5GB + bge-small). Coder-7B loads on demand in
remaining VRAM/RAM. Full fallback path in §18.

---

## 11. Management UI → L5

> L5 bar, tested live: *"non-eng volunteer onboards a new agent role (defines job, tools,
> guardrails) in under 10 min unassisted"* — with a volunteer **the team did not choose**, and
> the role must then actually work.

**Implementation baseline (12 July 2026):** the root Next.js frontend is accepted as complete and is
frozen for the three-person backend/model work split. The requirements below are therefore acceptance
criteria for the existing interface, not an assignment to scaffold another dashboard. Remaining work
may provide backend APIs, realtime compatibility, authentication hardening and regression verification;
it must not silently claim an unimplemented screen as evidence.

### 11.1 Role Builder — the entire L5 test surface, built as a wizard

Five screens, every field defaulted, nothing free-form except the job description:

1. **Job** — "What should this specialist do?" One text box, plain English. (Dictate it via
   Wispr Flow — power-up evidence in the same breath.) An SLM converts it to a persona draft,
   shown for approval, editable.
2. **Brain** — model picker: 3 cards ("Fast/Balanced/Code-focused"), one pre-selected based on
   the job text. No model names required knowledge.
3. **Tools** — checkboxes with human labels ("Read project files", "Search the live web",
   "Run tests", "Post GitHub comments"). Dangerous grants (merge, delete) show an inline
   warning chip.
4. **Guardrails** — sliders/toggles: max spend per task, max seconds, "requires critic
   approval" (default ON), "can act without human review" (default OFF), escalation trigger.
5. **Test flight** — the wizard runs the new role against a canned sample task *right there*,
   shows the output, and offers "Activate". Activation registers the role in Convex; the
   Planner can delegate to it on the next matching task.

**Rehearsal protocol:** run the 10-minute test with 3 non-engineers before judging (hostel
mates, other-track participants). Every place they hesitate is a UI bug — fix the copy, add
the default, shorten the step. The volunteer test is won in rehearsal, not on stage.
**Planned volunteer role:** "Changelog specialist" — safe tools, obvious job description,
visibly works on first task.

### 11.2 The rest of the operator surface

- **Assign work**: paste an issue URL or type/dictate a request → task enqueued (the rubric's
  "control surface lets a non-engineer assign work" — also wired to voice via ElevenLabs).
- **Review queue**: escalations with full artifact context; approve / edit-and-approve / reject
  (rejections auto-capture eval cases, §9.3).
- **Pause/resume** any agent or the whole crew (one switch — also the emergency brake if the
  demo goes sideways).
- **Prompt editor** with version bump + diff + "run Gauntlet before save" button.
- **Policy editor** — the `policy/*.yaml` files rendered as forms, committed via write-back.

Docs: a one-page illustrated quickstart (satisfies the L3 "PM with docs" floor independently,
in case the live volunteer test goes badly — never leave a parameter resting on a single
live moment).

---

## 12. Power-ups

All five, each doing real work, each with pre-staged evidence. +125.

| Power-up | Real use in Hermes | Evidence ready |
|---|---|---|
| **Convex** (+25) | THE control plane: task queue, traces, all memory layers, eval store, alerts, role registry, live dashboard subscriptions. Remove Convex and nothing runs. | Repo (schema + functions) + Convex dashboard showing live tables during a run. |
| **Cloudflare** (+25) | Workers: GitHub webhook ingress (the front door of the whole product). Pages: management UI + live docs site (real surface #3). Workers AI: inference fallback. | Live URLs + CF dashboard with request logs during judging. |
| **Linkup** (+25) | Research Expert's live-web tool: searches error strings, upstream issues, dependency changelogs mid-triage; results land in the `research` artifact, cited in Hermes's GitHub replies ("upstream regression in libfoo 2.4.1 — [link]"). | Code + a live query during a judged run; the citation visible in the posted GitHub comment. |
| **ElevenLabs** (+25) | Voice does real work both directions: (a) alert firings announced aloud; (b) daily standup digest ("Hermes handled 14 issues, merged 2 PRs, 1 escalation waiting"); (c) voice-assign work from the dashboard mic. | Live demo of voice-assign → task appears in queue → completes. |
| **Wispr Flow** (+25) | All prompt/persona/policy authoring and issue-reply editing during the event done by dictation; the Role Builder job-description field is the natural home. | Wispr stats screenshot ≥500 words (accumulates trivially over the build — screenshot on day 1 evening *and* before judging). |

---

## 13. Technology stack

| Layer | Choice | Note |
|---|---|---|
| Inference | llama.cpp (server mode, multi-slot) + GGUF | Grammar-constrained JSON for all fast-lane outputs |
| Models | Qwen3-8B-Q4 (planner/critic), Qwen3-4B-Q4 (triage/docs/etc.), Qwen2.5-Coder-7B-Q4 (code experts), bge-small (embeddings) | Personas share weights; ~3 model files cover 10+ roles |
| Fine-tuning | PEFT + TRL; QLoRA by default on constrained VRAM, ordinary LoRA when the base fits | Offline, reviewed data only; versioned adapters are evaluated, converted to GGUF and loaded separately by llama.cpp |
| Runtime | Python 3.12, asyncio, FastAPI (local API), Pydantic (artifact schemas) | |
| Control plane | **Convex** | Queue, traces, memory, evals, alerts, roles |
| Ingress | **Cloudflare Worker** | Webhook HMAC verify + normalize + enqueue |
| Frontend | Existing root Next.js 16 + React 19 + TypeScript + Tailwind + Zustand + `@xyflow/react`, deployed on **Cloudflare Pages** | Accepted/frozen visual implementation; backend compatibility gateway projects canonical events |
| Desktop shell | Tauri wrapping the dashboard | Keeps the PRD's desktop-app identity; browser tab is the judging fallback |
| Real surface | GitHub REST + webhooks (PyGithub / httpx) | The only credentialed component |
| Live search | **Linkup** SDK | Research Expert tool |
| Voice | **ElevenLabs** TTS + STT | Alerts out, assignments in |
| Local telemetry | psutil + nvidia-smi | Model-timeline view |
| Evals/CI | pytest harness + GitHub Actions | Branch protection = the real gate |

Approved scope change (12 July 2026): LoRA/QLoRA training is now included. Train one high-volume
Qwen3-4B triage/reply/docs adapter first; keep Planner base-first and keep Critic independent from the
adapter that produced the artifact it judges. Training uses reviewed, licensed and sanitized data with
strict train/dev/held-out splits. The Gauntlet is never training data. Promotion requires base/tokenizer
hash compatibility, baseline-versus-adapter gains, no safety regression, latency/memory acceptance,
three stable final eval runs and a demonstrated rollback. Closed-loop failures remain pending review
and never enter training automatically.

Still deliberately cut for the hackathon: Docker (native only), SQLite (Convex replaces it), and the
Windows/Linux/macOS support matrix (demo machine only).

---

## 14. Data model

Convex tables (abridged — full schema in `convex/schema.ts`):

```
tasks        id, source(github|ui|voice), type, repo, payload, status
             (pending|claimed|running|done|failed|escalated), lease, result_urls[]
runs         id, task_id, plan_artifact, status, started, finished,
             total_cost, total_cost_cloud_equiv, total_latency, agent_versions
spans        (see §8.1)
artifacts    id, run_id, type, schema_version, content, produced_by_span
agents       name, version, origin(kickoff|spawned), persona, weights, tools[],
             guardrails{max_cost, max_seconds, needs_critic, autonomous}, active
entities     kind(user|issue|repo), key, snapshot, history[]
policies     path, yaml, git_sha            (mirror of policy/ in git)
eval_cases   id, source(seeded|captured), input, golden, status(active|pending-review)
eval_runs    id, agent_versions, per_case_results[], pass_rate, ci_ref
alert_rules  id, predicate, channel(banner|voice)
alert_events id, rule_id, run_id, fired_at, message
```

Workspace on disk: `workspace/<task_id>/` → git worktree (deep lane) + `artifacts/*.json` +
`logs/`. Artifacts are dual-written (disk for agents, Convex for dashboard/trace) by the
runtime, in the same step-completion transaction.

---

## 15. Autonomy & guardrail policy

The line between L4 ("human approves every step") and L5 ("escalates by exception only") is a
*policy*, so we make the policy explicit, versioned, and visible (`policy/autonomy.yaml`):

**Fully autonomous (no human in the loop):**
- Labels, classification, priority, milestone assignment
- Replies: answers, clarification requests, dup notices
- Closing exact duplicates (similarity > threshold AND critic pass) with a link
- Opening fix PRs; **merging** PRs that are: small (< policy line-limit), CI fully green,
  critic-passed, security-expert clean, and not touching `autonomy.yaml`-listed protected
  paths (auth, release workflow, policy dir itself)
- Docs-only merges with green CI; draft (not published) releases

**Escalate by exception (with full artifact context, never a restart):**
- Security-labeled issues; breaking API changes; protected paths; low planner confidence;
  two consecutive critic rejections; any budget breach; angry-user sentiment flag

**Hard never (enforced in the write-back layer, not by prompts):**
- Force-push, branch deletion, repo settings, secrets access, publishing a release,
  writes to any repo not in the allowlist, exceeding per-task spend cap

The mentor question "what stops it going rogue?" is answered by opening this file and the
write-back layer's allowlist code — enforcement in code, not in prompt vibes.

---

## 16. Demo runbook

**T-24h:** freeze agent versions (tag `agents-v4`); run Gauntlet 3× and bookmark results;
verify webhook path with a test issue; charge everything; screenshot Wispr stats; confirm the
bookmarked diff pair + fired alert exist; brief the whole team on the mentor scripts in §8.3.

**Setup (5 min):** dashboard on screen 1 (run list + live queue), GitHub repo on screen 2,
`nvidia-smi`/model-timeline visible, ElevenLabs audio on, QR code up.

**The 10-minute judged demo:**

| Min | Beat | Rubric row it lands |
|---|---|---|
| 0–1 | Frame: "This is the maintainer-on-duty for a real repo. It ran last night unattended — here's the log." Show completed runs with GitHub URLs. | Working product |
| 1–3 | **Mentor files a real issue from their own account. Stopwatch.** Dashboard shows plan DAG forming, parallel branches, critic pass, reply + labels land on GitHub. ~45s, trace shows $0.00. | Working product, cost/latency |
| 3–4 | Open that run's trace tree: who called whom, tokens/cost per node, the memory pack it loaded, the policy ids it cited. | Observability, memory |
| 4–6 | Trigger the Rust issue → **spawn moment**: `rust-expert` born mid-run, visible in trace + registry. Show a critic `revise` bounce with notes. | Org L5 |
| 6–7 | Diff view: bookmarked pass/fail pair across versions; alert log with the real firing (voice announces one if a fresh alert triggers). Eval chart: pass rate v1→v4; show the CI-blocked PR. | Observability, evals |
| 7–9 | **Volunteer (mentor's pick) builds "Changelog specialist" in Role Builder.** Team silent. Role runs its first task. | Management UI L5 |
| 9–10 | Overflow pitch: release the backlog, queue visibly drains, counter of completed-real-tasks ticks up. Voice-assign one task by mic. Leave it running. | Overflow, ElevenLabs |

**Standing overflow loop (rest of judging):** every QR-filed issue → completed → +20. One team
member watches the escalation queue; interventions are legitimate (that *is* the L5 design) but
each autonomous completion is points, so keep the machine fed.

**If something breaks mid-demo:** pause switch → "this is the operator's emergency brake —
also a feature" → resume or fall back to the recorded run walkthrough in the trace viewer
(observability L5 means the past runs are always demoable).

---

## 17. Build plan

Team of 3; 36 buildable hours per member. The visual frontend is an accepted frozen input. No member is
assigned to recreate it. The remaining work is split evenly across runtime execution, durable control
plane/external effects, and model-quality/realtime/reliability proof.

| Hours | Member 1 — Runtime | Member 2 — Control plane | Member 3 — Model quality and proof |
|---|---|---|---|
| 0–4 | Python runtime, Pydantic mirror, in-memory adapter, model bootstrap | Bun/root integration, contracts, Convex/Worker, GitHub App | Eval/training schema, hardware/base audit, data governance, gateway fixture |
| 4–10 | Planner/DAG/artifacts/critic and real maintainer fast lane | Webhook→lease→trace→exactly-once comment/labels | Gateway prompt/event path, `agents-v1`, initial cases, data pipeline |
| 10–18 | Maintainer deep lane, worktrees, safe commands and complete task coverage | PR/write-back gates, policy, protected paths and canonical subscriptions | 40-case maintainer Gauntlet, builder/security suites, QLoRA run |
| 18–26 | Builder lane, defensive security-audit lane, spawn/escalation | Builder/security contracts, findings, memory, multi-repo, adapter registry, providers | Adapter export/model card, base-vs-adapter report, live gateway, failure matrix |
| 26–30 | Resume/outbox, adapter loader, telemetry, latency/security hardening | CI gate, idempotency/privacy/outage tests, deployment | v2→v4 comparisons, three final evals, E2E/performance/promotion/rollback proof |
| 30–34 | Joint integration and runtime-owned blocker fixes | Joint integration and live-service validation | Three-mode acceptance, documentation and evidence capture |
| 34–36 | Warm models and runtime operations | Service/GitHub operations and emergency modes | Two rehearsals, evidence index and fallback replay |

Primary acceptance runs are: (1) judge-authored maintainer issue to real GitHub reply in under one
minute, (2) scoped product brief/feature to tested PR, and (3) allowlisted read-only repository audit to
redacted evidence-backed report plus a separately approved remediation PR.

If only one GPU is available, training windows are reserved in advance. QLoRA never competes with
llama.cpp demo latency/evidence runs, and no training job runs after the final configuration freeze.

**Scope-cut order if behind** remains: Tauri shell (browser is fine) → voice-assign (keep text and voice
alerts) → role self-adjust (keep spawn) → secondary hosted/docs polish → second-repository polish.
Never cut the maintainer vertical slice, trace evidence, independent critic, eval gate, hard write-back
policy or adapter rollback. Builder/security breadth may be reduced to one strong end-to-end fixture
each, but their common contracts and safety boundaries remain.

---

## 18. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| "Your repo is staged" challenge | Medium | 80→48 pts | Judge-authored issues live (unanswerable); repo #2 with organic pre-event history; commit-linked real bug fixes. Lead with the live filing. |
| GPU too slow / VRAM overflow on demo box | Medium | Cost/latency L5 | Pinned-set memory math done up front (§10.5); fallback ladder: 4B planner → Workers AI for planner only (still <$0.01/task, and it *strengthens* the CF power-up) → Claude Haiku planner (~$0.004/run, still 25× under bar). Decide at T-24h, freeze. |
| Sub-60s missed live | Low-Med | L5→L4 on 1x param | 16s slack in budget; rehearse with cold caches; worst case 70s still lands L4 band's top — small loss, don't panic on stage. |
| Planner JSON plans malformed | Medium | Run failures → success % | Grammar-constrained decode; plan-schema validator with one auto-repair retry; template plan fallback for the fast lane (fixed DAG is invisible if never triggered — and log honestly when it is). |
| Volunteer flubs Role Builder | Medium | UI L5→L3/4 | 3 rehearsals with strangers; defaults everywhere; the docs page secures L3 floor regardless. |
| Hermes posts something wrong/rude on real GitHub | Low | Credibility | Critic gate + voice policy + profanity/sentiment check in write-back; everything is edit/delete-able; an honest correction + auto-captured eval case is a *good* story (closed loop, live). |
| GitHub rate limits / webhook flake mid-judging | Low | Demo stall | GitHub App auth (5k/hr); poller fallback if webhooks lag; pause switch + trace-viewer walkthrough of past runs as the graceful degrade. |
| Convex/network outage at venue | Low | Everything | Phone hotspot tested; runtime buffers trace events locally and replays; fast lane can run queue-less from the local poller cache. |
| Critic too strict → escalates everything (L5 autonomy lost) | Medium | 80-pt param | Tune critic thresholds against Gauntlet during phase 4; track escalation rate on the analytics view; target <15% (that *is* the 85% bar). |

---

## 19. Scoring math

| Parameter | Weight | Level | Points | Won by |
|---|---|---|---|---|
| Working product | 20× | L5 | 80 | Real GitHub + live docs site; judge-filed issues; 85% × 3 runs on eval dashboard; exception-only escalation (§6, §15) |
| Org structure | 5× | L5 | 20 | Per-request DAGs, critic revise loop, mid-run `rust-expert` spawn, blocked-artifact escalation, role self-adjust (§5) |
| Observability | 7× | L5 | 28 | Live trace trees, per-node cost, filters/search, diff view, real fired alerts (§8) |
| Evals | 5× | L5 | 20 | 40-case Gauntlet, CI gate w/ real blocked merge, auto-captured failures, v1→v4 chart (§9) |
| Handoffs & memory | 2× | L5 | 8 | Artifact-only handoffs + entity memory + policy layer, rubric's three layers by name (§7) |
| Cost & latency | 1× | L5 | 4 | 44s / $0.00 live with stopwatch (§10) |
| Management UI | 1× | L5 | 4 | Volunteer role-build <10 min, rehearsed ×3 (§11) |
| **Base** | | | **164** | |
| Power-ups | | 5/5 | **+125** | §12 |
| Overflow | | uncapped | **+20 × n** | QR pipeline + backlog drain + live fixes (§6.3) |
| **Floor at n=10 overflow tasks** | | | **489** | |

Realistic degraded case (one param slips to L4, one power-up disputed, n=5): ~390. Still a
winning posture — the architecture has no single point of scoring failure.

---

## 20. Definition of Done

Ship nothing that isn't on this list; everything on this list is demoable in under 60 seconds.

**Working product**
- [ ] Judge can file an issue from their phone and watch the reply land on GitHub in <60s
- [ ] 3 recorded full-gauntlet runs at ≥85%, dashboard page bookmarked
- [ ] At least one autonomously merged fix PR with green CI in repo history
- [ ] Escalation queue shows a real exception with full context attached

**Org**
- [ ] Two saved runs with visibly different plan DAGs for different request shapes
- [ ] One saved run with a critic `revise` → improved artifact chain
- [ ] The spawn demo (Rust issue) reproduces on demand; registry shows `origin: spawned`

**Observability**
- [ ] Any past run findable via search in <15s and walkable step-by-step
- [ ] Cost-by-agent question answerable from analytics without touching a keyboard shortcut
- [ ] Bookmarked diff pair + at least one real alert firing in the log

**Evals**
- [ ] Gauntlet ≥40 cases, runnable in one command and in CI
- [ ] Screenshot + live link to a genuinely blocked merge
- [ ] One captured-from-failure eval case traceable failure→capture→CI
- [ ] v1→v4 pass-rate chart with git tags

**Multipurpose modes and LoRA**
- [ ] One scoped builder request produces requirements, code, tests, security evidence and a real PR
- [ ] One read-only repository audit produces normalized redacted findings with zero GitHub mutations
- [ ] One separately approved remediation task produces a tested PR and rescan delta
- [ ] QLoRA/LoRA candidate has dataset manifest, model card, adapter/base hashes and GGUF load proof
- [ ] Frozen base-versus-adapter report shows quality, safety, latency and memory; losing adapter is not promoted
- [ ] Critic does not use the producer adapter; adapter rollback is demonstrated and audited

**Memory**
- [ ] Second issue from same account gets a history-aware reply
- [ ] Policy edit in UI → next run's trace cites the new rule id

**Cost/latency**
- [ ] 10 consecutive fast-lane runs all <60s, trace cost <$0.01 shown per run

**Management UI**
- [ ] 3 rehearsal strangers each built a working role in <10 min, zero help
- [ ] Pause switch, review queue, voice-assign all work on the demo box

**Power-ups**
- [ ] Convex dashboard, CF dashboard + live URLs, Linkup query in a judged run,
      voice demo, Wispr screenshot ≥500 words — all in the evidence folder

---

*Helios plans. The runtime executes. The experts specialize. The critic validates.*
*Hermes delivers — on a real repo, in under a minute, for free.*
