# Team Member 3 — Management UI, Desktop Shell, Docs, Voice, and Demo

## Mission

You own everything a judge, maintainer, community manager, or non-engineer sees and operates. Your
job is to make the work produced by Members 1 and 2 understandable, controllable, and demonstrably
real. The dashboard must answer: what work entered, what plan was formed, which agents acted, what
they read and produced, how much it cost, why the critic accepted or rejected it, what landed on
GitHub, and what requires a human.

You also own the L5 non-engineer test: a volunteer must create and activate a working specialist in
under ten minutes without help. The Role Builder, review queue, pause control, prompt/policy editors,
voice assignment, alert playback, Tauri shell, public docs site, and evidence package are not separate
side projects; they are one operator experience built on the same contracts.

Your work must function before the real runtime and backend exist. Build a fixture-backed data adapter
and complete every screen with deterministic seed records. Switch to Convex queries without changing
component props. Never wait for models or GitHub credentials to begin.

### Scope invariant

`soul.md` remains the product feature source of truth. This three-person plan redistributes its full
hackathon scope; it does not authorize the old scope-cut list or remove Tauri, multi-repo, voice,
overflow, self-adjustment, hosted fallback, any maintainer task type, or any evidence requirement.
Fixtures keep development moving but never replace the live implementation or final proof.

## What the other two members own

### Member 1 — Runtime and Intelligence

Member 1 owns `runtime/`, `agents/`, and `evals/`. They produce plans, spans, typed artifacts, model
telemetry, critic verdicts, spawned-agent events, role-version diffs, escalations, Gauntlet results and
write-back intents. You visualize these records but do not reinterpret or silently repair them.

### Member 2 — Control Plane and Integrations

Member 2 owns `convex/`, `apps/worker/`, `packages/contracts/`, `policy/`, `.github/`, root scripts,
Cloudflare bindings, GitHub App/write-back, task leases, memory persistence, eval capture, alerts and
server-side ElevenLabs calls. You consume generated Convex APIs and the shared contract package. You
never place GitHub, ElevenLabs, Cloudflare or runtime bearer secrets in browser code.

## Repository ownership

You may edit these paths without coordination:

```text
apps/dashboard/
apps/desktop/
apps/docs/
evidence/
```

Do not directly edit:

```text
runtime/                         # Member 1
agents/                          # Member 1
evals/                           # Member 1
convex/                          # Member 2
apps/worker/                     # Member 2
packages/contracts/              # Member 2; imported, never duplicated
policy/                          # Member 2; edited only through the product UI/API
.github/                         # Member 2
package.json                     # Member 2 owns root orchestration
pnpm-workspace.yaml              # Member 2
.env.example                     # request additions from Member 2
README.md                        # Member 2 owns root run instructions
```

Your app-specific `package.json`, Vite config, Pages config, Tailwind config, Tauri config and docs
configuration remain in your owned directories.

## Shared architecture and the no-blocking rule

Implement one `DataProvider` interface with two adapters:

```text
FixtureDataProvider   → static shared JSON fixtures and local interactive mutations
ConvexDataProvider    → generated Convex queries/mutations/actions
```

All pages and components consume provider hooks, never raw fixture imports and never direct fetches
inside presentation components. The environment flag `VITE_DATA_MODE=fixture|convex` selects the
adapter. This lets you finish UI and rehearse while Members 1 and 2 are still integrating.

Freeze this provider-to-Convex map with Member 2 at hour 2. Fixture methods must have the same input,
loading/error shape and return type:

| UI capability | Member 2 function(s) |
|---|---|
| Task list/detail/assignment | `tasks.list`, `tasks.get`, `tasks.enqueueFromUi` |
| Approved backlog | `tasks.validateApprovedBacklog`, `tasks.enqueueApprovedBacklog` |
| Run list/detail/compare | `runs.list`, `runs.get`, `runs.compare` |
| Trace and artifacts | `spans.listByRun`, `artifacts.listByRun`, `artifacts.get` |
| Agents, prompts and Role Builder | `agents.list`, `agents.getVersions`, `agents.createRoleDraft`, `agents.createVersionDraft`, `agents.startTestFlight`, `agents.activateVersion`, `agents.setActive` |
| Reviews | `reviews.list`, `reviews.get`, `reviews.approve`, `reviews.editAndApprove`, `reviews.reject` |
| Evals | `evalCases.list`, `evalCases.approve`, `evalCases.reject`, `evalRuns.list`, `evalRuns.get`, `evalRuns.start` |
| Alerts | `alerts.listRules`, `alerts.saveRule`, `alerts.listEvents`, `alerts.acknowledge` |
| Policy | `policies.list`, `policies.validateDraft`, `policies.saveDraft` |
| Controls | `system.get`, `system.setGlobalPause`, `system.setAgentPause`, `system.setWritebackMode` |
| Repository health | `repositories.listHealth` |
| Analytics | `analytics.costByAgent`, `analytics.latencyByType`, `analytics.modelTimeline` |
| Voice | `voice.transcribeAssignment`, `voice.synthesizeAlert`, `voice.generateStandup` |

Only the provider adapters call these generated functions. The only direct HTTP reads allowed in UI
infrastructure are safe `GET` health/status calls to `VITE_WORKER_URL` and `VITE_RUNTIME_URL`; no
presentation component fetches them itself.

The final repository is expected to run with:

```bash
pnpm install
python -m pip install -e "runtime[dev]"
pnpm dev
```

You are responsible for making these app-specific commands work so Member 2 can compose them:

```bash
pnpm --filter dashboard dev
pnpm --filter dashboard build
pnpm --filter dashboard test
pnpm --filter docs dev
pnpm --filter docs build
pnpm --filter desktop tauri dev
pnpm --filter desktop tauri build
```

## Shared contracts you consume

Import domain types from `@hermes/contracts`. Do not define local copies of `Task`, `Run`, `Span`,
`Artifact`, `Agent`, `EvalRun`, `AlertEvent`, `ReviewItem`, `Policy`, or `WritebackAction`.

Assume the following key relationships:

```text
Task 1 ── N Runs
Run  1 ── 1 PlanArtifact
Run  1 ── N Spans
Run  1 ── N Artifacts
Span 0..1 parentSpanId → Span
Span 0..1 outputArtifactRef → Artifact
Agent name + version → producing spans/artifacts
Run  0..N resultUrls → real GitHub artifacts
Alert 0..1 runId → Run
ReviewItem 1 runId + artifact chain → operator decision
```

Important semantic rules:

- Show `costUsd` and `costCloudEquivalentUsd` as different metrics; never relabel equivalent cost as
  actual spend.
- Show fallback flags and planner fallback honestly.
- `origin: spawned` must be visually distinct and show its birth run/time.
- Failed commands and failed tests remain red even if later work passes.
- A critic `revise` is a visible edge back to the producer, not silently folded into the final result.
- GitHub work counts as complete only when a `resultUrl` exists.
- Fixture, dry-run, failed, cancelled and queue-only items never increment the completed-real-task
  counter.
- Protected/private artifact fields must use the redacted operator projection Member 2 supplies.

## Required environment variables

Request these browser-safe entries in Member 2's `.env.example`:

```text
VITE_DATA_MODE=convex
VITE_CONVEX_URL=
VITE_WORKER_URL=http://127.0.0.1:8787
VITE_RUNTIME_URL=http://127.0.0.1:8788
VITE_GITHUB_REPO_URL=
VITE_DOCS_URL=
VITE_DEMO_MODE=1
VITE_ENABLE_VOICE=1
VITE_ENABLE_TAURI=1
```

Never use any variable beginning with `GITHUB_APP_PRIVATE`, `GITHUB_TOKEN`, `ELEVENLABS_API_KEY`,
`CLOUDFLARE_API_TOKEN`, `HELIOS_RUNTIME_TOKEN`, or `LINKUP_API_KEY`. Vite exposes prefixed values to
the browser bundle; secrets must remain server-side.

## Dashboard implementation layout

Create a clear feature-oriented structure:

```text
apps/dashboard/
├─ package.json
├─ vite.config.ts
├─ tsconfig.json
├─ tailwind.config.ts
├─ wrangler.toml
├─ public/
│  ├─ logo.svg
│  ├─ demo-qr.svg
│  └─ manifest.webmanifest
├─ src/
│  ├─ main.tsx
│  ├─ app.tsx
│  ├─ routes.tsx
│  ├─ styles.css
│  ├─ providers/
│  │  ├─ data-provider.tsx
│  │  ├─ fixture-provider.tsx
│  │  ├─ convex-provider.tsx
│  │  ├─ theme-provider.tsx
│  │  └─ audio-provider.tsx
│  ├─ fixtures/
│  │  ├─ index.ts
│  │  └─ mutable-store.ts
│  ├─ components/
│  │  ├─ shell/
│  │  ├─ common/
│  │  ├─ task/
│  │  ├─ run/
│  │  ├─ trace/
│  │  ├─ artifact/
│  │  ├─ agent/
│  │  ├─ eval/
│  │  ├─ policy/
│  │  ├─ alert/
│  │  ├─ review/
│  │  ├─ voice/
│  │  ├─ backlog/
│  │  └─ command/
│  ├─ features/
│  │  ├─ overview/
│  │  ├─ tasks/
│  │  ├─ runs/
│  │  ├─ run-detail/
│  │  ├─ run-compare/
│  │  ├─ agents/
│  │  ├─ role-builder/
│  │  ├─ reviews/
│  │  ├─ evals/
│  │  ├─ alerts/
│  │  ├─ models/
│  │  ├─ policies/
│  │  ├─ prompts/
│  │  └─ settings/
│  ├─ hooks/
│  ├─ lib/
│  │  ├─ formatting.ts
│  │  ├─ search.ts
│  │  ├─ diff.ts
│  │  ├─ dag-layout.ts
│  │  ├─ downloads.ts
│  │  └─ redaction.ts
│  └─ test/
└─ index.html
```

Use React, TypeScript, Tailwind, React Router, React Flow, Recharts, a small accessible component
library, and a maintained structured diff component. Do not introduce multiple overlapping UI kits.

## Required routes and exact contents

### `/` — Operations overview

Show, in this order:

1. Global live/dry-run state and emergency pause switch.
2. Pending/running/done/escalated counters.
3. Completed-real-task counter where each item links to GitHub.
4. Live queue with source, task type, repository, age, lease/runtime and state.
5. Active run strip with current node, elapsed time, actual cost and lane.
6. Last-24-hour success rate, escalation rate, median latency and actual spend.
7. Current model status/VRAM summary.
8. Recent alerts and review items.
9. Approved-backlog batch card showing queued/running/completed/escalated counts and a stop button
   that invokes global pause; every completed item must link to its real GitHub result.

The page must continue updating without manual refresh through Convex subscriptions.

Add an operator command/chat drawer available from every route. It is a focused control surface, not
a fake general-purpose chatbot: the operator can type or dictate a maintainer request, paste an issue
URL, ask to open the matching task/run, and receive a confirmation preview before enqueueing. Status
answers must be assembled from live Convex records with links; never ask an LLM to invent system
state. Submitting work calls the same assignment mutation as `/tasks`.

### `/tasks`

- Search and filter by source, type, repo, status and date.
- Show lease owner/expiry for active work.
- Show result URLs and terminal reason.
- Provide assignment composer: issue URL, plain request or microphone.
- Allow safe retry only for failed tasks and explain that retries create a new run.
- Provide an **Approved backlog release** panel. The operator pastes/selects existing issue URLs,
  runs Member 2's validation, reviews accepted/rejected reasons, then confirms one batch. Show a loud
  warning that this creates real GitHub work, the write-back mode, batch size, repository breakdown,
  and a cancel button before confirmation. Never offer “generate issues” or count queued fixtures.
- Show each released batch as a live drain with immutable batch ID and links to every terminal result
  or escalation.

### `/runs`

- Filter by task type, agent, status, repo, date and fallback usage.
- Full-text search over the redacted searchable projection of prompts/artifacts/errors.
- Columns: start time, task, repo, lane, status, latency, actual cost, cloud-equivalent cost, agent tag,
  fallback flags and GitHub result.
- Provide stable URLs and a compare checkbox.

### `/runs/:runId`

This is the principal judging screen. Include:

- Header with task, repo, lane, status, stopwatch, cost, result links and replay/fallback badges.
- Plan DAG rendered with React Flow; node colors reflect lifecycle state.
- Expandable trace tree aligned to DAG nodes.
- Critic revision edges and concrete notes.
- Span detail drawer: agent/version, model, prompt hash, timings, tokens, costs, tools, error/verdict,
  input/output artifact links and policy IDs.
- Artifact viewer with JSON, formatted domain view, raw/redacted indicator and download.
- Memory-pack viewer separated into NOW, THIS USER'S PAST and BUSINESS POLICY.
- Model timeline aligned with the run.
- Escalation context if present.
- GitHub write-back audit and resulting URLs.

### `/runs/compare`

Accept `left` and `right` run IDs in the URL. Align spans primarily by plan node/role, not array index.
Show:

- Plan structure differences.
- Agent and version changes.
- Prompt-hash and policy-version differences.
- Input/output artifact diff.
- Verdict and error divergence.
- Token, latency, actual cost and equivalent-cost deltas.
- Test result and GitHub result differences.

Include a one-click bookmarked v1-failing/v4-passing pair in demo mode.

### `/agents`

- Registry cards/table with name, job, model, tools, guardrails, origin, version and active state.
- Visually distinguish kickoff, spawned and Role Builder roles.
- Show persona/version diff and the run that caused self-adjustment.
- Show birth timestamp and parent run for spawned roles.
- Permit pause/resume, not destructive deletion.
- Link to the Role Builder.

### `/agents/new` — five-step Role Builder

Implement the exact wizard promised in `soul.md`:

1. **Job:** one plain-language text box; generate a persona draft and allow editing.
2. **Brain:** Fast, Balanced and Code-focused cards; preselect from job text.
3. **Tools:** human-language checkboxes. Dangerous tools show warnings and require explicit opt-in.
4. **Guardrails:** max spend, max seconds, critic approval, autonomous action and escalation trigger.
5. **Test flight:** enqueue a `role_test`, stream its run, show output, then Activate.

Persist draft state between steps and page refreshes. Defaults must be safe: critic required, autonomous
off, minimal tools, bounded time/cost. Step 1 calls `agents.createRoleDraft` and subscribes to its
persona-draft task; step 5 calls `agents.startTestFlight`; Activate calls
`agents.activateVersion` only for the unchanged passing draft hash. Never call the localhost runtime
with a browser token and never edit YAML directly.

### `/reviews`

Show escalations and human-gated actions with the complete artifact chain. Provide:

- Approve.
- Edit and approve, with a clear human-edited badge.
- Reject with reason.
- Open source issue/PR.
- Compare proposed vs edited artifact.

Every rejection/edit explains that Member 2 will capture an eval candidate. Monetary, security,
protected-path, release-publication and policy-write decisions remain clearly human-gated.

### `/evals`

- Current agent tag and threshold status.
- v1→v4 pass-rate chart.
- Triage, response and fix breakdown.
- Repeated-run stability and latest three complete runs.
- Case table with source, tags, scorer, result and linked failure trace.
- Pending captured cases with approve/reject actions.
- CI check/blocked-PR link.
- Downloadable JSON report.

### `/alerts`

- Rule editor for failure, cost spike, latency spike, escalation, lease expiry, model outage and eval
  regression.
- Firing log with timestamp, observed value, baseline, run link, severity and acknowledgement.
- Voice toggle/test button.
- Never synthesize or replay private issue content; use server-provided safe alert text.

### `/models`

- Current model processes, status, loaded/pinned state, slots and endpoint health.
- RAM/VRAM utilization chart.
- Load, request, completion and eviction timeline.
- Cold-start versus generation latency.
- Actual local/remote fallback indicator.
- No fabricated GPU data when telemetry is unavailable; show `Unavailable` with reason.

### `/policies`

Render `triage.yaml`, `autonomy.yaml`, `escalation.yaml` and `voice.yaml` as understandable forms while
preserving a raw YAML advanced view. Show stable rule IDs, active Git SHA, version history and diff.
Validate draft through Member 2 before enabling Save. Saving creates a Git-backed audit trail.

### `/prompts`

- List agent prompt/persona versions.
- Edit draft, view diff, increment version.
- Persist edits through `agents.createVersionDraft`; an active version remains immutable.
- `Run Gauntlet before save` action with streamed status.
- Start that run through `evalRuns.start` and subscribe by returned eval-run/task ID; do not call the
  localhost protected endpoint from browser code.
- Block activation when eval thresholds fail.
- Link every active version to its Git tag/commit when available.

### `/settings`

- Service health for Convex, Worker, runtime, model servers, GitHub, Linkup, ElevenLabs and Pages.
- Global pause and write-back mode, with confirmation for moving to live mode.
- Demo repository/allowlist shown read-only.
- Show both onboarded repositories, connection/last-webhook state and active policy version; never
  expose installation IDs or secrets.
- Links to docs, Worker status and live GitHub repo.

## Visual and interaction requirements

- Optimize for a 1440p projector, then 1024px laptop, then mobile status/review use.
- Use semantic color plus icons/text; color alone cannot communicate pass/fail.
- Support keyboard navigation and visible focus for every control.
- Use accessible labels, dialogs, tabs and form errors.
- Meet WCAG 2.1 AA contrast in the dashboard itself.
- Use skeletons for loading, empty states for missing data and actionable error messages.
- Preserve deep links across refreshes.
- Avoid animation that delays comprehension; live DAG transitions should be subtle and optional.
- Keep the active run legible at a distance: large state, elapsed time, cost and result.
- Add a reduced-motion mode and respect OS preference.

## Voice and Wispr Flow

### Voice assignment

1. Use `MediaRecorder` with explicit mic permission and recording state.
2. Cap duration and show elapsed time.
3. Send audio to Member 2's server-side transcription action.
4. Display transcript for confirmation/editing.
5. Convert to a task only after confirmation.
6. Show the queued task immediately and link to its run.

If mic or ElevenLabs is unavailable, the same text field remains fully functional.

### Voice alerts and standup

Subscribe to alert events. Request safe synthesized audio from Member 2 only when voice is enabled.
Queue at most one playback at a time, allow mute, display the same text, and retain the alert in the
log. Add a standup button that requests the daily digest text/audio and links each statistic to runs.

### Wispr Flow

Wispr acts as OS-level dictation, so do not build a fake API integration. Ensure Role Builder job,
prompt editor, policy fields, review edits and assignment text areas behave correctly with dictation:
no keybinding traps, premature submission or aggressive auto-formatting. Member 3 captures the required
usage screenshot and records where dictation was used during the live demo. The evidence is not
complete until the Wispr stats screenshot visibly shows **at least 500 dictated words**. Capture one
screenshot on day 1 evening and a fresh screenshot before judging; keep both timestamped originals in
`evidence/power-ups/wispr/`.

## Tauri desktop shell

Create:

```text
apps/desktop/
├─ package.json
├─ src-tauri/
│  ├─ Cargo.toml
│  ├─ tauri.conf.json
│  ├─ capabilities/
│  └─ src/main.rs
└─ README.md
```

Wrap the same dashboard URL/build. Keep privileges minimal: normal window, safe external-link opening,
optional tray status and no arbitrary shell command capability. Display connection health and fall back
to the hosted Pages URL when the local dashboard is unavailable. The browser version remains the demo
fallback and must have full feature parity.

## Public docs site

Create `apps/docs/` as a lightweight static site deployable to Cloudflare Pages. It must include:

- One-sentence product framing and architecture diagram.
- Five-minute operator quickstart with screenshots.
- How to assign work and interpret a run.
- How to review an escalation.
- Role Builder walkthrough.
- Autonomy and hard-never policy explanation.
- Privacy/on-device inference explanation.
- Demo repository and live status links.
- Honest limitations and emergency pause procedure.
- Developer setup generated from Member 2's root commands.

The Docs expert's docs-only GitHub write-back should be capable of updating this site, proving the
second real surface.

## Demo and evidence package

Own this structure:

```text
evidence/
├─ README.md
├─ run-ids.md
├─ urls.md
├─ screenshots/
├─ recordings/
├─ evals/
├─ alerts/
├─ role-builder/
├─ power-ups/
└─ rehearsal-log.md
```

Record exact live URLs and IDs for:

- Judge-authored issue fast-lane run.
- Real green fix PR.
- Different plan DAG pair.
- Critic revise→pass run.
- Spawned `rust-expert` run.
- Blocked/escalated run.
- Run diff pair.
- Real alert firing.
- v1→v4 eval chart and three ≥85% runs.
- Genuinely CI-blocked PR.
- Memory-aware second interaction.
- Policy edit affecting the next run.
- One genuine completed task from the second onboarded repository with isolated policy/memory.
- Role Builder activation/test flight.
- Convex/Cloudflare/Linkup/ElevenLabs/Wispr evidence.

Use this exact power-up proof checklist; a logo or dependency alone is not evidence:

| Power-up | Required proof in `evidence/power-ups/` |
|---|---|
| Convex | schema/functions commit, live deployment URL, screenshot of real task/run/span/artifact rows, and the judged run ID visible in both dashboard and Convex |
| Cloudflare | Worker and both Pages URLs, deployed commit SHAs, request-log screenshot for the judged webhook, and one recorded Workers AI fallback attempt/result |
| Linkup | research span/artifact with query, retrieval time and source URL, plus the resulting GitHub reply containing the real citation |
| ElevenLabs | recording of voice assignment → confirmed transcript → queued task, a spoken real alert, and daily standup audio/text with linked runs |
| Wispr Flow | timestamped day-1 and pre-judging stats screenshots with the latter visibly at **≥500 words**, plus a recording of Role Builder dictation without manual retyping |

Store a short `README.md` inside each provider folder naming the real run/task IDs, URLs, capture
time, team member who captured it, and what the proof demonstrates. Redact secrets and private issue
content; do not crop away timestamps, provider identity, or run linkage.

Never fabricate evidence. A fixture is acceptable for UI development but must be labelled fixture and
must not appear in the final evidence folder as a real completion.

## Hour-by-hour execution plan

### Hours 0–2 — Shell, provider boundary and fixture screens

- Scaffold dashboard, routing, design tokens, shell navigation and `DataProvider` interface.
- Import Member 2's contracts or temporary exact fixtures.
- Build fixture mode with one fast run, one deep run, one revision, one spawn, one escalation, one
  eval regression and one alert.
- Agree with Member 2 on query/mutation names and with Member 1 on artifact display names.
- Scaffold docs and Tauri directories without waiting for final branding.

**Handoff at hour 2:** a navigable fixture dashboard and list of missing contract fields.

### Hours 2–6 — Live vertical-slice dashboard

- Build overview, task list, run list, basic run detail, DAG and trace tree.
- Connect Convex provider as soon as Member 2 exposes task/run/span/artifact queries.
- Show the first real webhook task and deterministic runtime completion live.
- Add result URL, pause switch and write-back mode indicator.

**Exit test:** issue creation becomes a live queue item, run and GitHub result without refreshing.

### Hours 6–11 — Production trace and observability

- Finish span drawer, artifact viewer, memory/policy display and GitHub audit.
- Build search/filter, run compare, cost analytics and model timeline.
- Make critic revise edges and spawned-agent birth visible.
- Add bookmarked demo run support.

### Hours 11–17 — Operator controls and Role Builder

- Implement five-step Role Builder with safe defaults, test flight and activation.
- Implement assignment composer, command/chat drawer, approved-backlog validation/release, review
  queue and global/per-agent pause.
- Implement policy and prompt editors with validation/diff/Gauntlet gate.
- Rehearse the Role Builder once with a teammate who did not implement it and fix every hesitation.

### Hours 17–22 — Evals, alerts and voice

- Build eval dashboard and pending captured-case review.
- Build alert rules/log and text/audio playback.
- Implement microphone assignment confirmation flow and daily standup playback.
- Test degraded text-only behavior with ElevenLabs disabled.
- Ensure all relevant text fields work with Wispr dictation.

### Hours 22–27 — Desktop, docs and Cloudflare Pages

- Finish Tauri shell with minimal capabilities and hosted fallback.
- Finish quickstart/operator docs and architecture/policy pages.
- Deploy dashboard and docs with Member 2.
- Add QR code linking to the demo issue form/repository.
- Verify repository filters/settings and capture the second-repository real-task proof.
- Test projector, laptop and phone layouts.

### Hours 27–31 — Completeness and accessibility

- Finish settings/health, empty/error states, downloadable evidence and all cross-links.
- Run keyboard-only and contrast checks.
- Verify every `soul.md` mentor question can be answered from a screen in under 15 seconds.
- Conduct three non-engineer Role Builder rehearsals; record time and confusion points.
- Fix copy/defaults rather than coaching the user.

### Hours 31–34 — Integration freeze and evidence

- Rebase on `integration`; switch production build to Convex mode.
- Run dashboard/docs/desktop tests and root `pnpm build`/`pnpm test` with Member 2.
- Capture exact run IDs, GitHub URLs, screenshots, eval reports, alert event and power-up evidence.
- Verify both Wispr screenshots exist and the pre-judging statistic visibly exceeds 500 words.
- Freeze navigation and layout; make only blocker fixes.
- Cache a fixture replay of the full demo for network/model fallback, clearly labelled historical run.

### Hours 34–36 — Full judged-demo rehearsal

- Run the ten-minute script twice with the same screens/order used during judging.
- Measure how long every navigation step takes.
- Place bookmarked tabs, QR code and audio controls.
- Verify browser fallback before Tauri.
- During judging, you operate the dashboard and narration; Members 1 and 2 watch runtime/control health.

## Required tests

### Component and contract tests

- Every shared fixture renders without runtime exceptions.
- Unknown optional fields degrade gracefully; unknown schema versions show a clear incompatibility.
- Formatting keeps actual and equivalent cost distinct.
- Result URLs are safe external links.
- Redacted artifacts never reveal hidden fields.

### Live behavior

- New task, span, artifact, alert and review records appear without refresh.
- Active DAG nodes transition correctly.
- Search and filters find bookmarked runs in under 15 seconds.
- Compare aligns reordered spans by node/role.
- Pause state and write-back mode update across open clients.
- Backlog validation reasons render exactly; confirmation enqueues one batch and its live counters
  reconcile with terminal GitHub result URLs.
- The operator command/chat drawer uses live records for status and shares the normal assignment
  confirmation path.

### Role Builder and controls

- The wizard preserves state and enforces safe defaults.
- Dangerous tools require explicit confirmation.
- Test flight streams a real or fixture run and activation persists the role.
- Review approve/edit/reject creates the expected mutation and visible audit state.
- Policy invalid draft cannot save; valid save shows resulting Git SHA/version.
- Prompt activation blocks after failed Gauntlet.

### Voice and fallback

- Mic permission denial leaves text assignment intact.
- Transcript requires confirmation before task creation.
- Multiple alerts do not overlap audio.
- Muting persists locally.
- ElevenLabs outage produces a text alert and no unhandled error.
- Wispr-compatible fields accept a 500+ word dictation session without accidental submit, lost text,
  shortcut conflicts or destructive auto-formatting.

### Accessibility and responsive behavior

- Keyboard-only completion of assignment, review and Role Builder.
- No critical automated accessibility violations on principal routes.
- Focus returns correctly after dialogs/drawers.
- Charts include accessible summaries and do not rely only on color.
- Core overview/run/review functions work at 1024px and on a phone.
- Reduced-motion setting disables nonessential transitions.

### Build/deploy

- Dashboard, docs and Tauri dev/build commands pass.
- Cloudflare Pages URLs serve the expected commit.
- Deep links survive direct navigation/refresh.
- Tauri opens external GitHub/docs links safely.
- Fixture and Convex production builds both succeed.

## Mentor-question readiness matrix

| Mentor question | Screen/action |
|---|---|
| Show a real completed task | Overview counter → GitHub result URL |
| Show a past run | Runs search → run detail |
| Who called whom? | Run detail trace tree/DAG |
| What did this agent receive and produce? | Span drawer → artifact refs |
| Which agent cost the most? | Runs analytics/cost-by-agent |
| Why did one run fail and another pass? | Run compare bookmarked pair |
| Did an alert really fire? | Alerts firing log and run link |
| Did a role appear mid-run? | Spawn run → agent birth → registry |
| Do agents revise each other? | Critic revise edge and notes |
| What does Hermes remember? | Run memory pack, three labelled layers |
| Does policy actually affect behavior? | Policy version/rule IDs in run |
| Do failures improve evals? | Failure trace → pending case → CI run |
| Can a non-engineer create a role? | Role Builder test flight |
| Can the crew be stopped? | Global pause plus live state change |
| Can it drain real work at volume? | Approved backlog batch → live drain → completed GitHub links |
| What prevents dangerous actions? | Policy screen and write-back audit |
| Is it really local/cheap? | Model timeline plus actual cost |

## Member 3 definition of done

- Every required route works with fixtures and live Convex data.
- A judge can watch an issue become a plan, trace and real GitHub result without refresh.
- Run detail exposes DAG, trace, artifacts, memory, policies, models, critic and write-back.
- Search, analytics, diff and alerts answer the four observability mentor questions immediately.
- Role Builder creates, tests and activates a working role in under ten minutes without coaching.
- Review queue, assignment, pause, prompts and policy editing work.
- Command/chat assignment and approved real-backlog release use the same audited task pipeline; the
  completed counter excludes fixtures and non-terminal work.
- Eval dashboard shows 40+ cases, version gains, repeated runs, captured failures and blocked CI.
- ElevenLabs voice assignment, alert and standup work with safe text fallback.
- Wispr dictation works in all promised fields and timestamped day-1/pre-judging evidence includes a
  visible ≥500-word statistic.
- Dashboard and docs are live on Cloudflare Pages; Tauri wraps the same experience.
- Evidence folder contains real, linked, timestamped proof for every rubric and power-up claim.
- Browser fallback can run the entire demo if Tauri fails.

## Merge and handoff checklist

1. Work on `member3/operator-ui`; never force-push after a checkpoint is consumed.
2. Merge fixture-mode UI at hour 6, observability at hour 11, controls at hour 22, and final UI at
   hour 31.
3. Before each merge, run:

   ```bash
   pnpm --filter dashboard test
   pnpm --filter dashboard build
   pnpm --filter docs build
   ```

4. At hour 31 also run Tauri build/dev smoke testing on the demo machine.
5. Do not edit contracts to satisfy the UI; report the exact missing field to Member 2 with a fixture.
6. Do not calculate authoritative run totals in the browser when Member 2 provides canonical totals.
7. Give Member 1 screenshots of any confusing artifact/span output so they can improve the producer.
8. Give Member 2 the exact query/index bottleneck rather than implementing browser-side table scans.
9. Final merge order is Member 2 root/contracts/control, Member 1 runtime, then your dashboard/docs/
   desktop changes. Resolve only path/config conflicts with all three present.
10. Validate from a clean browser profile with no cached auth, then repeat from the Tauri shell.
