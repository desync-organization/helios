# Hermes GitHub Connector — Product, UX, Architecture, and Implementation Specification

> Status: implementation specification  
> Version: 1.0  
> Updated: 12 July 2026  
> Product source of truth: `docs/soul.md`  
> Primary owner: Member 2 — control plane and external integrations  
> Coordinating owners: Member 1 for runtime contracts; Member 3 for gateway, evaluation, and evidence

## 1. Purpose

This document defines exactly how Hermes connects to GitHub, how the connection appears in the
frontend, how GitHub events become Helios tasks, and how approved agent output returns to GitHub.

The connector must make this product claim demonstrably true:

> Hermes replaces a repository's maintainer-on-duty rotation by receiving real GitHub work, forming a
> task-specific team of agents, independently validating the work, and safely writing useful results
> back to the same repository.

The connector is not a repository browser, an OAuth login button, a local `git` command wrapper, or a
chatbot that pastes generated review text. A completed connector task must create a real, useful GitHub
artifact and persist its URL.

Examples of terminal artifacts are:

- an issue comment or clarification request;
- labels or a milestone applied to an issue;
- an exact duplicate closed with a canonical link;
- a submitted pull-request review with inline comments;
- a GitHub Check Run with annotations;
- a branch and tested pull request;
- a policy-qualified merge;
- a draft release;
- a private security report reference or separately authorized remediation pull request.

Generating a plan, local patch, review draft, test log, or queued write-back intent is not completion.

## 2. Relationship to the existing product

### 2.1 Existing implementation

The current frontend already contains:

- Blueprint Canvas;
- Chat;
- God Mode Terminal;
- Workstation;
- Cost Dashboard;
- Multiverse branch visualization;
- Settings with GitHub and Vercel connection controls;
- a Zustand orchestrator store and compatibility WebSocket protocol.

The current GitHub settings flow accepts a classic personal access token, validates it using
`GET /user`, and writes it to a local env file. The current `/api/git` route executes a small allowlist
of local Git commands. These are development-era capabilities. They are not the production connector
described by this document.

### 2.2 Frontend freeze

`docs/soul.md` currently declares the presentation frontend frozen. The frontend sections below are a
precise target design, not authorization to modify presentation components. Before implementing them,
the three members must record a frontend scope change in `docs/soul.md` and allocate an owner.

Until that happens, backend integration must project into the existing reachable surfaces:

- Settings shows connection health using its current integration area;
- Chat accepts a GitHub issue, pull request, or repository URL;
- Blueprint shows agent activity if the current store consumes the status event;
- God Mode shows redacted progress, test, policy, critic, and write-back events;
- Workstation shows generated code artifacts where already supported;
- completion contains the real `githubUrl`;
- cost and token events contain measured values only.

Do not claim a task queue, run-detail page, exception inbox, or comparison UI until that surface exists
and is reachable.

## 3. Product principles

The connector must obey the following rules.

1. **GitHub App, not shared PAT.** Production automation acts as a repository-installed GitHub App.
2. **Least privilege.** Repositories and permission classes are selected explicitly at installation.
3. **Credentials stay server-side.** The browser, gateway, and local model runtime never receive the
   GitHub App private key, client secret, webhook secret, or installation token.
4. **Webhook-first.** GitHub events create work. Polling is only missed-event recovery.
5. **Fast acknowledgement.** Webhook ingress verifies, normalizes, enqueues, and returns without
   waiting for inference.
6. **Convex is canonical.** The browser, Cloudflare Worker, gateway, and runtime do not maintain
   competing task databases.
7. **Artifact-only agent handoffs.** Agents exchange versioned typed artifacts, not hidden chat state.
8. **Independent critic.** The agent that produced an outbound artifact cannot approve it.
9. **Policy at the mutation boundary.** Prompts may recommend an action; deterministic server code
   decides whether it is allowed.
10. **Idempotency everywhere.** Replayed webhooks and retried write-backs produce one external result.
11. **Fresh-state validation.** Repository, SHA, permission, pause, checks, and policy state are checked
    immediately before mutation.
12. **Result URL or no completion.** A live task is completed only after the GitHub API returns a
    persisted URL or verifiable target identity for the mutation.
13. **Exceptions preserve context.** A human receives the decision, evidence, attempts, risk, and
    recommended action; they do not restart the task.
14. **Security findings are private by default.** Read-only audit and remediation are separate actions.
15. **Honest telemetry.** Local actual cost and estimated cloud-equivalent cost are separate fields.

## 4. User roles

### 4.1 Installation administrator

Can install or remove the GitHub App, choose repositories, accept permission changes, configure
repository policy, and enable write-back modes.

### 4.2 Repository operator

Can view tasks and traces, pause work, approve exceptions, request a rerun, and change behavior within
the administrator's policy envelope.

### 4.3 Repository contributor

Interacts from GitHub through issues, pull requests, comments, reviews, and Check Run actions. A
contributor does not need a Hermes account to receive normal public repository responses.

### 4.4 Auditor

Has read-only access to runs, artifacts, policy decisions, write-back audits, and evidence. Restricted
security findings require separate authorization.

## 5. Primary user journeys

### 5.1 Install and activate Hermes

```text
Operator opens Integrations
→ clicks Install Hermes GitHub App
→ GitHub installation page opens
→ operator selects account and repositories
→ GitHub redirects to Hermes setup URL with installation_id and state
→ Hermes validates signed state and installation ownership
→ repositories are synchronized into Convex
→ operator configures autonomy and guardrails per repository
→ Hermes runs a read-only connection test
→ operator activates dry-run, PR-only, or live mode
```

Acceptance conditions:

- no PAT is pasted into the browser;
- selected repositories and granted permissions are shown accurately;
- changing installation repository access updates Hermes through installation webhooks;
- activation is impossible if required permissions are missing;
- read-only connection testing never mutates GitHub;
- every policy change is versioned and auditable.

### 5.2 Issue intake and triage

```text
GitHub issues.opened webhook
→ Cloudflare verifies signature and delivery identity
→ event is normalized and deduplicated
→ Convex creates one task
→ runtime claims task with repository memory and policy
→ Planner creates a task-specific DAG
→ Triage and Dedupe may run in parallel
→ Reply agent drafts result
→ independent Critic passes, revises, or blocks
→ write-back service revalidates policy and current issue state
→ labels/comment/duplicate action is written to GitHub
→ returned URL is persisted
→ task becomes completed
```

### 5.3 Pull-request review

```text
GitHub pull_request.opened or synchronize webhook
→ resolve current head SHA, base SHA, changed files, diff, checks, and repository policy
→ Planner selects language, test, security, and review specialists as needed
→ specialists produce evidence-backed review findings
→ findings are deduplicated and line locations are resolved against the current diff
→ Critic rejects weak, duplicated, stale, stylistic-only, or unsupported findings
→ write-back creates one pending GitHub review
→ valid inline comments are attached
→ review is submitted as COMMENT or REQUEST_CHANGES
→ GitHub Check Run is completed with summary, annotations, trace link, and requested actions
```

`APPROVE` must be disabled by default. It may be enabled only for repositories whose policy explicitly
allows agent approval and whose required tests, security checks, critic verdict, and freshness checks
all pass.

### 5.4 Review finding to automatic repair

```text
Hermes publishes a Check Run with a “Fix this” requested action
→ contributor clicks the action inside GitHub
→ check_run.requested_action webhook is verified
→ existing finding and run lineage are loaded
→ Planner creates a repair DAG
→ code specialist changes a task worktree
→ test and security specialists validate it
→ Critic reviews the exact patch hash
→ policy chooses a PR against the contributor branch or a separate remediation PR
→ result URL is added to the original Check Run and pull request
```

### 5.5 Bug issue to tested pull request

```text
Issue classified as reproducible bug
→ Reproduction agent creates a failing regression test
→ Code specialist produces the smallest patch
→ Test agent proves failure-before and success-after
→ Security agent reviews changed attack surface
→ Critic reviews patch, tests, security, scope, and evidence
→ write-back checks base SHA and protected paths
→ branch and PR are created
→ Check Run links the issue, run, tests, and critic verdict
→ optional merge occurs only under narrow repository policy
```

### 5.6 Exception escalation

Examples include protected paths, breaking changes, base conflicts, ambiguous duplicates, failed
checks, low confidence, security-sensitive work, and exceeded budgets.

The task remains resumable. The escalation artifact must include:

```text
escalationId
taskId
runId
repositoryId
reasonCode
decisionRequired
recommendedDecision
alternatives[]
evidenceArtifactIds[]
attemptedActions[]
riskIfApproved
riskIfRejected
expiresAt?
resumeNodeId
```

Approval resumes from `resumeNodeId`; it does not create a new context-free task.

## 6. Target frontend information architecture

### 6.1 Navigation

If frontend scope is reopened, use the existing shell and add these operator concepts without creating
a second application:

```text
Mission Control  — repository work queue and operational totals
Blueprint        — live manager/specialist plan and status
Task             — selected task, trace, artifacts, and proof
Workstation      — patch/files/test artifacts
Multiverse       — task worktrees and delivery branches
Evidence         — historical runs, comparisons, evals, and URLs
Settings         — installations, repositories, policies, and providers
```

Chat and God Mode should be available inside a selected task rather than competing with the task queue
as separate mental models. If retaining the existing nav is materially faster, map concepts as:

| Existing surface | Connector responsibility |
|---|---|
| Blueprint | active plan DAG and agent statuses |
| Chat | operator commands, issue/PR URL intake, and escalation decisions |
| God Mode | structured event stream projected to readable terminal lines |
| Workstation | patch, files, test output, and review artifacts |
| Multiverse | worktree/branch lineage, never arbitrary production Git operations |
| Cost Dashboard | measured token, latency, actual cost, and equivalent cost |
| Settings | GitHub App installations and repository policies |

### 6.2 Global header

Every connector-aware screen displays:

- selected GitHub account and repository;
- repository visibility icon;
- write-back mode: `dry-run`, `pr-only`, or `live`;
- security audit mode: `off` or `read-only`;
- connector health: healthy, degraded, disconnected, or permission change required;
- global pause/emergency stop;
- last successful webhook timestamp;
- a direct link to the repository on GitHub.

The mode badge must never be represented by color alone. Use text, icon, tooltip, and confirmation for
dangerous changes.

### 6.3 Empty state

When no installation exists, show one focused card:

```text
Connect GitHub

Install Hermes on selected repositories. Hermes receives issues and pull requests,
forms an engineering team, validates its work, and writes approved results back.

[Install GitHub App]

No personal access token required.
```

Below it, list the exact default permissions in plain language and link to a “Why these permissions?”
explanation.

### 6.4 Installation setup screen

Step 1 — **Select installation**

- GitHub account/avatar;
- installation health;
- repository selection scope: all repositories or selected repositories;
- granted permission summary;
- button to manage the installation on GitHub.

Step 2 — **Select repository**

- searchable list;
- owner/name;
- public/private/internal;
- default branch;
- archived/fork status;
- current installation access;
- readiness badge.

Archived repositories and unsupported forks are read-only unless policy explicitly allows them.

Step 3 — **Choose operating preset**

| Preset | Read | Comments/labels | PRs | Reviews | Merge | Security scan |
|---|---:|---:|---:|---:|---:|---:|
| Observe | yes | no | no | no | no | no |
| Triage | yes | yes | no | no | no | no |
| Maintainer | yes | yes | yes | yes | no | optional read-only |
| Trusted maintainer | yes | yes | yes | yes | narrow policy | optional read-only |

Step 4 — **Guardrails**

- protected path patterns;
- maximum changed files and lines;
- maximum task cost and latency;
- labels allowed for autonomous application;
- duplicate confidence threshold;
- required status checks;
- mergeable change types;
- egress policy for private content;
- security-audit opt-in;
- escalation recipients;
- retention policy.

Step 5 — **Connection test**

Run and display individual checks:

```text
✓ installation exists
✓ repository is accessible
✓ webhook delivery received
✓ metadata permission works
✓ issue permission works
✓ pull-request permission works
✓ checks permission works
✓ default branch resolved
✓ repository policy validated
— contents write not requested in Observe preset
```

Do not create a test comment or branch. If a mutation test is desired, require explicit confirmation
and use a dedicated test issue.

### 6.5 Mission Control

The default view answers “what work is Hermes responsible for now?”

Summary cards:

- active tasks;
- awaiting exception decisions;
- real GitHub completions today;
- rolling task success rate;
- median latency;
- actual local/provider cost;
- connector health.

Queue columns:

```text
GitHub item | task type | current stage | assigned agents | policy mode |
age | cost | exception | final result
```

Queue filters:

- repository;
- issue or pull request;
- task type;
- live/dry-run/fixture;
- running/completed/failed/escalated;
- agent;
- label;
- date range.

The “completed” filter must include only tasks with at least one persisted live GitHub result URL.

### 6.6 Task detail

Use three resizable panes.

#### Left pane — Plan

- original GitHub trigger;
- manager goal and acceptance criteria;
- plan DAG;
- agent name/version/model for each node;
- queued, active, blocked, revising, passed, or failed state;
- tool and budget grants;
- spawned specialists marked `origin: spawned`;
- current critical path.

Selecting a node filters the center and right panes to that node.

#### Center pane — Activity and trace

Display structured events as readable rows:

- time;
- actor;
- action;
- input artifact references;
- output artifact;
- tool invocation summary;
- latency;
- tokens;
- actual and equivalent cost;
- status/verdict.

Raw model chain-of-thought must never be displayed or persisted. Display concise decision summaries,
typed artifacts, tool evidence, and policy explanations.

#### Right pane — Proof

Tabs:

- **GitHub:** source item, current SHA, checks, review/write-back actions, result URLs;
- **Diff:** patch with changed lines and ownership/protection flags;
- **Tests:** commands, tool versions, exit codes, before/after results;
- **Security:** redacted findings and scan delta;
- **Critic:** criteria, verdict, revision notes, artifact hash;
- **Policy:** rule IDs, decision, denied actions, consent;
- **Cost:** per-node and total measured telemetry.

The primary completion action is `Open result on GitHub`, not “Download output.”

### 6.7 Exception inbox

Each card displays:

- exact decision in one sentence;
- why automation stopped;
- recommended option;
- evidence and affected files;
- risk of each option;
- task cost/time so far;
- expiry or staleness warning;
- `Approve once`, `Approve and update policy`, `Reject`, and `Add constraint` actions.

`Approve and update policy` requires administrator permission and creates a new versioned policy. It
must never silently broaden the current repository's authority.

### 6.8 Repository settings

Sections:

1. Connection and installation health
2. Repository access
3. Operating mode
4. Allowed autonomous actions
5. Protected paths and size limits
6. Required checks and merge policy
7. Security-audit consent
8. Data egress and providers
9. Memory and retention
10. Alert rules
11. Danger zone: pause, disconnect, delete derived memory

Show effective permissions from GitHub separately from policy permissions inside Hermes. For example:

```text
GitHub grants: Pull requests — write
Hermes policy: Pull-request creation — allowed; merge — denied
```

The narrower permission always wins.

### 6.9 GitHub-native UX

Hermes should remain useful without keeping its dashboard open.

#### Issue comment format

Use one concise, substantive comment:

```markdown
### Hermes triage

**Classification:** bug · priority P1
**Reproduction:** confirmed on `<short-sha>`
**Next action:** preparing a tested fix

I reproduced the failure when [...]. Tracking execution: [Hermes run](...)

<!-- hermes:task=<taskId>;action=<actionId> -->
```

Never expose model prompts, private traces, security secrets, or verbose agent conversation.

#### Pull-request review format

- one submitted review per head SHA;
- one overall summary;
- inline comments only for actionable, evidence-backed findings;
- no duplicate comments on unchanged lines;
- severity and confidence separated;
- link to test evidence and trace;
- previous review marked superseded after `synchronize`.

#### Check Run

Name: `Hermes / Engineering Review`

States:

```text
queued → in_progress → completed
```

Conclusions:

```text
success         no blocking findings and all required evidence passed
failure         deterministic tests/security checks failed
action_required human decision required
neutral         analysis completed but policy does not permit a blocking verdict
cancelled       task was paused or superseded
timed_out       bounded runtime expired
```

Output summary includes:

- plan summary;
- agents used;
- tests;
- security;
- critic verdict;
- policy result;
- actual duration and cost;
- real trace URL.

Requested actions, where policy allows:

- `fix_finding` — start a repair task;
- `rerun_review` — run against current head SHA;
- `explain_finding` — post a bounded evidence explanation;
- `escalate` — create an operator review item.

### 6.10 Accessibility and responsive behavior

- full keyboard navigation for queue, task nodes, tabs, and approvals;
- visible focus rings;
- status communicated by text and icon, not color alone;
- reduced-motion mode disables decorative Blueprint animations;
- screen-reader labels include repository, item number, state, and result;
- destructive or authority-expanding actions require explicit confirmation;
- desktop is the primary operational layout;
- tablet collapses the three-pane view into tabs;
- mobile supports monitoring and exception approval, not diff-heavy administration.

## 7. Recommended system architecture

```text
GitHub
  │ signed webhooks
  ▼
Cloudflare Worker — ingress only
  │ verify, normalize, dedupe key, enqueue
  ▼
Convex — canonical control plane
  │ tasks, runs, spans, artifacts, policy, repositories, audits
  │ claim/lease
  ▼
Helios local runtime
  │ plan, specialists, tools, tests, critic
  │ credential-free write-back intent
  ▼
Convex write-back queue
  │ current policy + lease + artifact hash
  ▼
GitHub write-back service
  │ mint scoped one-hour installation token
  │ re-read current GitHub state
  │ deterministic authorization
  ▼
GitHub REST/GraphQL/Git Data APIs
  │ result URL and API identifiers
  ▼
Convex audit + realtime cursor feed
  │
  ├─ WebSocket compatibility gateway → existing Next.js client
  └─ evidence reports and alerts
```

### 7.1 Trust boundaries

| Component | May read GitHub content | May hold GitHub credentials | May mutate GitHub |
|---|---:|---:|---:|
| Browser | redacted projection only | no | no |
| WebSocket gateway | redacted projection only | no | no |
| Cloudflare ingress | webhook payload as required | webhook secret only | no |
| Convex control plane | bounded normalized content | encrypted app configuration if server-only | queues only |
| Helios runtime | allowlisted task/repository context | no | no |
| Model server/agent | minimal task context | no | no |
| Write-back service | action-specific current state | app private key/server secret | yes, policy-gated |

Prefer keeping the GitHub App private key in the write-back service's secret manager rather than in
general-purpose Convex documents. Convex stores installation IDs and audit state, not minted tokens.

## 8. Framework and library comparison

### 8.1 GitHub integration framework

| Option | Advantages | Disadvantages | Fit for Hermes |
|---|---|---|---|
| Direct `fetch` | no dependency, works in Workers | manual auth, pagination, typing, previews, retries, and endpoint details | poor except for tiny ingress calls |
| `@octokit/rest` / `octokit` | official ecosystem, typed REST/GraphQL clients, pagination and plugins | authentication lifecycle still must be designed | good for API calls |
| `@octokit/app` | GitHub App JWT, installation clients, OAuth helpers, webhooks, official primitives | Node-focused; should not be forced into Worker ingress | **best for write-back service** |
| `@octokit/webhooks` | typed webhook names/payloads and signature verification | Node-oriented full package; Worker compatibility must be verified per build | good for types/tests; Worker may use Web Crypto directly |
| Probot | very fast standalone bot development, event routing, Octokit context, logging | introduces its own app lifecycle and server conventions around an architecture that already has Convex, Cloudflare, Helios, policy, and traces | good prototype, **not recommended as Hermes core** |

Decision:

- use `@octokit/app` in the server-side write-back service;
- use `octokit` or the installation-scoped client returned by `@octokit/app` for REST and GraphQL;
- use `@octokit/webhooks-types` for compile-time event payload types;
- use Web Crypto in Cloudflare Worker to verify the raw request body;
- optionally use `@octokit/webhooks` in Node integration tests to generate/verify fixtures;
- do not adopt Probot as the main runtime.

Reason: Probot is designed to be the framework hosting a GitHub App. Hermes already has a richer
execution framework and needs strict separation between webhook ingress, durable state, local agent
execution, and credentialed write-back. Direct Octokit primitives provide the required GitHub behavior
without creating a second orchestration layer.

### 8.2 Authentication choice

| Option | Scope model | Automation identity | Rotation | Recommendation |
|---|---|---|---|---|
| Classic PAT | broad user scopes | human user | manual, long-lived | remove from production |
| Fine-grained PAT | selected repos/permissions | human user | manual | local developer fallback only |
| OAuth App token | user authorization/scopes | user + app | token lifecycle | wrong primary model for repository automation |
| GitHub App user token | intersection of app and user permissions | user + app | expiring/refreshable | use only for explicitly user-attributed actions |
| GitHub App installation token | installation repositories and app permissions | Hermes App | expires after one hour | **default for autonomous actions** |

The production connector must never ask an operator to paste a classic PAT. Installation tokens should
be minted on demand, further narrowed to the target repository and action permissions, cached only for
their safe lifetime, and never persisted in logs or browser state.

### 8.3 Webhook ingress

| Option | Advantages | Disadvantages | Recommendation |
|---|---|---|---|
| Next.js Route Handler | simplest local development; shares app deployment | couples public ingress to UI deploy, weakens Cloudflare power-up, server/runtime limits | local fallback only |
| Probot Node server | convenient event handling | duplicate service lifecycle and state concerns | no |
| Convex HTTP action | close to canonical store | signature/raw-body and fast edge ingress are less isolated; long work must still be queued | viable but secondary |
| Cloudflare Worker | edge verification, Web Crypto, rate limiting, fast ack, queues, power-up evidence | Worker runtime compatibility constraints | **recommended** |

The Worker performs no inference and no GitHub write-back. It acknowledges after durable enqueue or a
bounded ingest attempt. If Convex is temporarily unavailable, use Cloudflare Queue retry and a dead
letter/audit path.

### 8.4 Durable orchestration

| Option | Advantages | Disadvantages | Recommendation |
|---|---|---|---|
| In-memory queue | easy | loses work on restart, no replay or audit | never |
| BullMQ + Redis | mature queue, retries, concurrency | adds Redis and a second durable state system | unnecessary for hackathon architecture |
| Inngest | developer-friendly durable event workflows | new external control plane and vendor dependency | reasonable alternative, not selected |
| Temporal | strongest mature workflow semantics | operationally heavy for current team/time | future enterprise option |
| Convex Workflow/Workpool | existing chosen backend, durable steps, retries, concurrency, reactive UI | component maturity and runtime limits must be tested | **recommended for control-plane workflows** |
| Helios scheduler alone | required for local model/tool execution | local process cannot be the only durable truth | execution worker, not sole orchestrator |

Use Convex for durable task state, leases, write-back workflows, retries, and realtime subscriptions.
Use Helios for dynamic agent DAG execution. Do not attempt to serialize arbitrary long-running local
model calls inside one Convex action.

### 8.5 Contracts and validation

| Option | Strengths | Weaknesses | Recommendation |
|---|---|---|---|
| handwritten TypeScript interfaces | zero runtime cost | no runtime validation | no |
| Zod | excellent TS ergonomics and ecosystem | Python mirrors still need generation/discipline | strong choice |
| TypeBox + Ajv | JSON Schema first, fast validation, cross-language friendly | more verbose | strong alternative |
| Valibot | small bundles | less useful than JSON Schema for Python boundary | frontend-only use at most |
| Convex validators only | native database validation | insufficient for Worker/runtime/shared package | not alone |

Decision: use Zod schemas in `packages/contracts` and export JSON Schema for Pydantic compatibility, or
choose TypeBox/Ajv if schema generation becomes unreliable. The key requirement is one versioned schema
source with fixture-based TypeScript/Python round-trip tests. Do not maintain unrelated handwritten
interfaces in each service.

Recommended packages:

```text
zod
zod-to-json-schema (only if compatible with selected Zod version)
@octokit/app
octokit
@octokit/webhooks-types
```

Pin exact versions in `bun.lock` after compatibility tests. Do not copy version numbers from this
document; package releases change.

### 8.6 Frontend server-state management

| Option | Fit |
|---|---|
| Zustand only | good for ephemeral UI and existing WebSocket projection; poor as a duplicate durable database |
| TanStack Query | excellent REST cache; duplicates some Convex realtime behavior |
| Convex React hooks | direct realtime canonical queries and mutations; best for new connector screens |
| Redux Toolkit | unnecessary additional state framework |

Decision:

- use Convex React queries/mutations for canonical tasks, repositories, runs, and review items if the
  browser is allowed to connect directly under authenticated, redacted functions;
- retain Zustand for local selection, pane layout, temporary filters, WebSocket compatibility, and the
  existing frozen client;
- never copy full Convex task tables into Zustand as a second source of truth;
- use TanStack Query only for endpoints not served by Convex, and only if such caching is needed.

### 8.7 Tables, graph, diff, and code views

| Need | Recommended library | Reason |
|---|---|---|
| plan/trace DAG | existing `@xyflow/react` | already installed and appropriate |
| virtual task table | `@tanstack/react-table` + `@tanstack/react-virtual` | headless, scalable, works with existing UI |
| patch/diff | `react-diff-view` or `@git-diff-view/react` after bundle/accessibility spike | proper unified/split diff behavior |
| code artifact | existing Workstation; Monaco only if editing is truly needed | avoid a large editor dependency for read-only proof |
| validation forms | `react-hook-form` + shared Zod schemas | nested policy forms and accessible errors |
| UI primitives | existing Radix/shadcn pattern | visual consistency and accessibility |
| notifications | existing Sonner | already installed |
| animation | existing Framer Motion, reduced-motion aware | already installed; use sparingly |

Do not add a heavy data grid or code editor until the task queue and diff requirements demonstrate the
need. Bundle size and demo reliability matter more than editor-like spectacle.

### 8.8 Observability

| Option | Advantages | Disadvantages | Recommendation |
|---|---|---|---|
| logs only | easy | cannot reach rubric target | no |
| Langfuse | agent/LLM tracing and evaluations | another hosted/local system and possible private-code egress | optional adapter |
| OpenTelemetry | vendor-neutral spans/metrics, production standard | UI/storage still required | recommended export format |
| Convex native spans + custom views | exact product semantics and realtime data | engineering work | canonical product record |

Persist product-level spans in Convex because task/artifact/write-back semantics are domain-specific.
Also export OpenTelemetry where practical. A third-party observability UI may be used, but it must not
become the only record or leak private repository content.

## 9. GitHub App registration

### 9.1 Registration fields

Create separate development and production GitHub Apps.

```text
Name: Hermes Maintainer (Dev/Production)
Homepage URL: <public Hermes URL>
Setup URL: <public Hermes URL>/api/github/setup
Webhook URL: <Cloudflare Worker URL>/webhooks/github
Webhook secret: secret-manager generated, high entropy
Expire user authorization tokens: enabled if user auth is used
Request user authorization during installation: off unless needed
```

The setup callback must carry and validate an application-generated, short-lived, single-use `state`
value tied to the authenticated Hermes operator.

### 9.2 Repository permissions

Request the smallest permission set that supports the shipped feature set.

| Permission | Initial level | Purpose |
|---|---:|---|
| Metadata | read | implicit repository identity and metadata |
| Issues | write | classify, label, milestone, comment, close exact duplicates |
| Pull requests | write | read diffs, submit reviews/comments, create and merge permitted PRs |
| Checks | write | Check Runs, annotations, requested actions |
| Contents | write | create branches/commits/PR patches; use read if write path is not shipped |
| Actions | read | inspect workflow runs when supported |
| Commit statuses | read | evaluate current status where required |
| Workflows | none | do not modify `.github/workflows` by default |
| Security events | none/read | request only for explicitly shipped security mode |
| Dependabot alerts | none/read | request only for opted-in dependency audit |

If GitHub requires a broader permission for a specific endpoint, document the endpoint and reason in
the onboarding UI before changing the app registration. Existing installations must approve added
permissions; surface `permission_change_required` as a health state.

### 9.3 Webhook subscriptions

Initial maintainer subscriptions:

```text
installation
installation_repositories
issues
issue_comment
pull_request
pull_request_review
pull_request_review_comment
check_run
check_suite
workflow_run
push
release
```

Subscribe to security/advisory/dependency events only when the corresponding permission and product
mode are implemented. Do not subscribe to every event “for future use.”

### 9.4 Event action allowlist

Normalize only useful actions. Example:

```text
issues: opened, edited, reopened, labeled, unlabeled, closed
issue_comment: created, edited
pull_request: opened, reopened, synchronize, ready_for_review, converted_to_draft, closed
pull_request_review: submitted, dismissed
pull_request_review_comment: created, edited
check_run: requested_action, rerequested
workflow_run: completed
installation: created, deleted, suspend, unsuspend, new_permissions_accepted
installation_repositories: added, removed
```

Ignore unsupported actions with an audited `ignored` result, not an error.

## 10. Webhook ingress implementation

### 10.1 Required headers

Reject requests missing:

```text
X-GitHub-Delivery
X-GitHub-Event
X-Hub-Signature-256
Content-Type: application/json
```

Enforce a bounded body size before parsing.

### 10.2 Verification algorithm

1. Read the raw request body exactly once as bytes/text.
2. Import the webhook secret using Web Crypto HMAC SHA-256.
3. Sign the raw bytes.
4. Compare the supplied `sha256=<hex>` signature in constant time.
5. Reject invalid signatures with a generic `401`; never log either signature.
6. Parse JSON only after verification.

### 10.3 Normalized event

```ts
type GitHubEventEnvelope = {
    schemaVersion: "1";
    deliveryId: string;
    event: string;
    action: string;
    installationId: number;
    repositoryId: number;
    repositoryNodeId: string;
    owner: string;
    repo: string;
    senderId: number;
    senderLogin: string;
    senderType: string;
    occurredAt: number;
    receivedAt: number;
    sourceObject: {
        type: "issue" | "pull_request" | "review" | "comment" | "check_run" | "workflow_run" | "installation";
        number?: number;
        nodeId?: string;
        url?: string;
        headSha?: string;
        baseSha?: string;
    };
    payloadRedacted: Record<string, unknown>;
    dedupeKey: string;
};
```

Do not place arbitrary full webhook bodies into the task table. Retain only bounded, redacted fields
required to resolve the source object. Fetch current state from GitHub when execution or write-back
begins.

### 10.4 Deduplication

Use two identities:

- delivery identity: `deliveryId` prevents exact webhook replay;
- semantic identity: repository + event + action + source object + relevant SHA/version prevents two
  equivalent deliveries from producing two tasks.

Store delivery receipt before returning success. Replays return `202` with the original ingest ID and
do not enqueue another task.

### 10.5 Bot-loop suppression

Ignore events authored by the Hermes bot when they correspond to a recorded write-back action. Embed a
hidden marker in comments and store returned GitHub node/database IDs. Do not suppress all bot events;
other automation may legitimately create work.

### 10.6 Response behavior

```text
202 accepted              verified and durably queued
200 duplicate/ignored     verified but no new task
400 malformed             invalid headers/JSON/schema
401 invalid signature     generic response
413 oversized             body limit exceeded
429 ingress limited       Retry-After supplied
503 ingest unavailable    only after bounded queue/Convex failure
```

Target webhook handler latency: below 500 ms at p95, excluding external outage. Inference never occurs
inside the request.

## 11. Canonical data contracts

### 11.1 Repository connection

```ts
type GitHubRepositoryConnection = {
    schemaVersion: "1";
    repositoryId: string;
    githubRepositoryId: number;
    githubNodeId: string;
    installationId: number;
    owner: string;
    name: string;
    fullName: string;
    visibility: "public" | "private" | "internal";
    defaultBranch: string;
    archived: boolean;
    fork: boolean;
    permissionsGranted: Record<string, "read" | "write">;
    writebackMode: "dry-run" | "pr-only" | "live";
    writebackOptIn: boolean;
    securityAuditOptIn: boolean;
    allowedActions: GitHubWritebackActionType[];
    protectedPaths: string[];
    requiredChecks: string[];
    maxChangedFiles: number;
    maxChangedLines: number;
    maxTaskCostUsd: number;
    allowedCloudProviders: string[];
    policyVersion: string;
    health: "healthy" | "degraded" | "disconnected" | "permission_change_required";
    lastWebhookAt?: number;
    synchronizedAt: number;
};
```

### 11.2 Write-back intent

The runtime may create only a credential-free intent:

```ts
type GitHubWritebackIntent = {
    schemaVersion: "1";
    actionId: string;
    idempotencyKey: string;
    taskId: string;
    runId: string;
    repositoryId: string;
    installationId: number;
    actionType: GitHubWritebackActionType;
    target: {
        issueNumber?: number;
        pullNumber?: number;
        checkRunId?: number;
        baseBranch?: string;
        baseSha?: string;
        headSha?: string;
    };
    artifactId: string;
    artifactHash: string;
    criticArtifactId: string;
    criticVerdict: "pass";
    policyVersion: string;
    requestedAt: number;
};
```

The content body, labels, review comments, patch reference, or release draft is read from the immutable
artifact matching `artifactHash`. Do not trust a second unreviewed body embedded in the intent.

### 11.3 Write-back action record

```ts
type GitHubWritebackAction = {
    schemaVersion: "1";
    actionId: string;
    idempotencyKey: string;
    taskId: string;
    runId: string;
    repositoryId: string;
    installationId: number;
    actionType: GitHubWritebackActionType;
    targetSnapshot: Record<string, unknown>;
    artifactId: string;
    artifactHash: string;
    criticArtifactId: string;
    policyVersion: string;
    policyRuleIds: string[];
    permissionSnapshot: Record<string, string>;
    status: "queued" | "authorizing" | "executing" | "succeeded" | "denied" | "failed" | "ambiguous";
    attempts: number;
    githubRequestId?: string;
    githubObjectId?: string;
    resultUrls: string[];
    denialCode?: string;
    errorCode?: string;
    createdAt: number;
    finishedAt?: number;
};
```

### 11.4 Action types

```ts
type GitHubWritebackActionType =
    | "issue_comment"
    | "labels_set"
    | "milestone_set"
    | "duplicate_close"
    | "check_run_create"
    | "check_run_update"
    | "pull_request_review"
    | "branch_and_pr"
    | "pull_request_merge"
    | "release_draft"
    | "security_remediation_pr"
    | "sarif_upload";
```

Do not add generic `github_api_call` or `git_command` action types. Every effect must have a bounded,
validated schema and explicit policy.

## 12. Write-back service

### 12.1 Responsibilities

The write-back service is the only component allowed to:

- read the GitHub App private key;
- mint installation access tokens;
- call credentialed GitHub mutation endpoints;
- perform Git-over-HTTPS authentication if required;
- translate successful results into canonical URLs and audit records.

It must not:

- run models;
- reinterpret the requested content;
- override a critic;
- modify policy;
- accept raw arbitrary GitHub API paths from the runtime;
- execute shell commands received through an intent.

### 12.2 Authorization pipeline

Before every mutation:

1. Load the current repository connection by internal repository ID.
2. Confirm GitHub repository ID and installation ID match the intent.
3. Confirm installation remains active and repository remains accessible.
4. Read global pause, repository pause, write-back mode, and security mode.
5. Confirm the run still owns a valid lease or approved resumable write-back grant.
6. Load the immutable artifact and recompute its content hash.
7. Confirm the independent critic passed that exact hash.
8. Load the current policy version; if changed, re-evaluate under the newer policy.
9. Confirm action type is allowed by both GitHub permission and Hermes policy.
10. Fetch current GitHub target state.
11. Confirm head/base SHA and target state are not stale.
12. Check protected paths, patch limits, required checks, security state, and spend/action limits.
13. Scan outbound content and patch for suspected secrets.
14. Atomically claim the idempotency key.
15. Mint an installation token narrowed to the target repository and required permissions.
16. Execute exactly one typed action handler.
17. Persist request ID, GitHub object identity, URLs, and result.
18. Emit completion only after persistence succeeds.

### 12.3 Token handling

- create installation tokens on demand;
- limit token repository IDs and permissions when GitHub permits;
- cache only in protected server memory with expiry earlier than GitHub's expiry;
- never store tokens in Convex documents, logs, traces, exceptions, or browser responses;
- clear cached tokens after installation suspension/removal or permission change;
- redact `Authorization`, cookies, private keys, client secrets, and webhook secrets from errors.

### 12.4 REST versus GraphQL versus Git Data API

Use:

- REST for mutations, checks, reviews, comments, labels, releases, and explicit endpoint semantics;
- GraphQL for consolidated read queries when it materially reduces requests and has tested permission
  behavior;
- Git Data API for small complete-content patch commits when consistent with `soul.md`;
- local `git` in isolated task worktrees for building, testing, and producing patch artifacts;
- Git-over-HTTPS only inside the credentialed delivery boundary if pushing a prepared commit is chosen.

Never use the local `/api/git` browser route as production GitHub write-back.

### 12.5 Idempotency and ambiguous failures

For each action, derive an idempotency key from:

```text
repositoryId + target identity + action type + artifact hash + relevant SHA
```

On timeout or network failure after a request may have reached GitHub:

1. mark the action `ambiguous`;
2. do not automatically repeat the mutation;
3. query GitHub using the hidden marker, object ID, branch name, commit SHA, or Check Run external ID;
4. if found, reconcile as succeeded and store its URL;
5. if absence is proven and retry policy allows, execute one bounded retry;
6. otherwise escalate with full context.

### 12.6 Rate limiting

Read and persist relevant GitHub rate-limit headers. On `403` or `429`:

- honor `Retry-After` when supplied;
- if remaining requests are zero, wait until the reset timestamp;
- otherwise use exponential backoff with jitter and a bounded attempt count;
- lower repository concurrency during secondary rate limiting;
- never continue hammering the API;
- expose connector degradation and a durable alert.

Limit content-creating actions separately from reads. Coalesce labels and review comments into fewer
requests where correct.

## 13. Action handler specifications

### 13.1 Issue comment

Inputs:

```text
issueNumber, bodyArtifactId, expectedIssueState?, marker
```

Checks:

- issue exists in the allowlisted repository;
- issue is not locked unless policy permits;
- body is substantive, bounded, redacted, and critic-approved;
- an identical Hermes marker/comment does not already exist;
- security-sensitive content is not being disclosed publicly.

Result: comment HTML URL.

### 13.2 Labels set

Inputs:

```text
issueNumber, desiredLabelNames[], expectedCurrentLabels[]?
```

Checks:

- each label is on the repository policy allowlist;
- dangerous workflow labels such as release/deploy/security publication labels require escalation;
- concurrent human label changes are preserved unless policy explicitly defines authoritative label
  ownership.

Prefer additive/removal deltas over blindly replacing all labels.

### 13.3 Duplicate close

Inputs:

```text
issueNumber, canonicalIssueNumber, duplicateConfidence, evidenceArtifactId
```

Checks:

- canonical issue exists and is not the same issue;
- both items belong to the same repository unless cross-repo policy explicitly permits linking;
- confidence meets deterministic policy threshold;
- evidence identifies the same root problem, not merely similar language;
- comment is posted before close;
- security-sensitive duplicates are escalated.

Result URLs: duplicate comment and closed issue.

### 13.4 Pull-request review

Inputs:

```text
pullNumber, expectedHeadSha, event, summary, comments[]
```

Each comment contains:

```text
path, line, side, startLine?, startSide?, body, findingId, evidenceArtifactIds[]
```

Checks:

- expected head SHA equals the current head SHA;
- each line exists in the current diff;
- comments are actionable and non-duplicated;
- no previously submitted identical finding exists for the same head SHA;
- `REQUEST_CHANGES` has at least one policy-defined blocking finding;
- `APPROVE` is separately enabled and all gates pass.

Create a pending review, attach all valid comments, then submit once. If any line mapping is stale,
remove that inline comment from the batch, preserve it in the trace, and either post it as a bounded
summary finding or rerun against the new SHA. Never attach a comment to the wrong line.

### 13.5 Check Run

Use a stable `external_id` containing the run ID, not private data. Set `details_url` to an authenticated
redacted run view. Update the same Check Run across queued, in-progress, and completed states.

Annotations are limited and batched according to GitHub API constraints. Prioritize blocking findings,
then warnings, then notices. The full record remains in Hermes.

### 13.6 Branch and pull request

Inputs:

```text
baseBranch, baseSha, branchName, commitMessage, patchArtifactId,
title, body, linkedIssueNumbers[], draft
```

Checks:

- base SHA remains current or policy explicitly permits rebasing through a new validated run;
- branch name is deterministic and namespaced, for example `hermes/task-<short-id>`;
- branch does not already point to unrelated work;
- complete patch matches the critic-approved hash;
- changed paths and sizes pass policy;
- tests and security artifacts are green;
- no secret is detected;
- `.github/workflows/**`, auth, payments, migrations, and policy-defined protected paths escalate;
- issue linkage is valid.

Prefer one branch/PR per task. If a branch already exists for the same idempotency key, reconcile rather
than create another.

### 13.7 Merge

Disabled by default.

Required gates when enabled:

- repository opted into autonomous merge;
- PR was created or explicitly admitted under the policy;
- head SHA equals the validated SHA;
- not draft;
- mergeable state is clean;
- required reviews and status checks pass;
- no unresolved blocking review threads;
- critic passed exact patch hash;
- no security finding above configured threshold;
- change type and size are in autonomous merge allowlist;
- protected paths and breaking changes are absent;
- global/repository pause is off immediately before mutation.

Never bypass branch protection, required checks, or repository rulesets.

### 13.8 Release draft

Hermes may create or update a draft release when policy allows. Publication is always human-controlled.
The draft must record target commitish, included PRs, generated notes evidence, tests, and known risks.

### 13.9 Security remediation

Security scan output cannot directly create a public issue or comment. A remediation PR requires:

- repository `securityAuditOptIn`;
- a separate remediation approval or standing remediation policy;
- redacted findings;
- exact affected commit SHA;
- fix tests and rescan;
- private handling until disclosure policy permits otherwise.

## 14. Runtime integration

### 14.1 Task claim

The runtime receives:

- bounded normalized GitHub source object;
- repository descriptor without credentials;
- current task facts;
- relevant repository/entity memory;
- policy pack and stable rule IDs;
- allowed tool grants;
- token, time, cost, and patch budgets;
- lease ID and expiry.

### 14.2 Repository checkout

The runtime may not mint an installation token. Choose one of these controlled patterns:

1. preferred: credential broker creates a short-lived, repository-scoped clone credential and injects
   it into an isolated checkout operation without returning it to the model process;
2. server prepares a repository snapshot/worktree and passes a verified local path to the runtime;
3. public repositories may use unauthenticated read-only clone under rate and provenance controls.

The model receives file contents and tool results, never the credential. Command environments must
remove credential variables and redact remote URLs containing credentials.

### 14.3 PR review context pack

Provide only what the plan needs:

```text
repository identity
base/head SHA
PR title/body/author association
changed file manifest
bounded diff chunks
relevant CODEOWNERS/policies
required checks and their state
linked issues
prior Hermes findings for this PR/SHA
repository memory relevant to changed paths
```

Large diffs are chunked by file and dependency relation. Planner must escalate when the diff exceeds
configured review coverage rather than claim full review.

### 14.4 Critic contract

The critic receives:

- acceptance criteria;
- outbound artifact;
- evidence artifacts;
- test/security results;
- policy rule IDs;
- changed paths and size;
- source SHA;

It does not receive the producer's hidden reasoning. Its output is a typed verdict:

```text
pass | revise | blocked
```

`pass` signs the outbound artifact hash. One bounded revision is allowed; two equivalent rejections
escalate.

## 15. Realtime and frontend contracts

### 15.1 Canonical event

```ts
type ConnectorEvent = {
    schemaVersion: "1";
    eventId: string;
    sequence: number;
    type: string;
    taskId: string;
    runId?: string;
    spanId?: string;
    parentSpanId?: string;
    nodeId?: string;
    repositoryId: string;
    timestamp: number;
    classification: "public" | "private" | "restricted";
    source: "github" | "control_plane" | "runtime" | "writeback";
    payload: Record<string, unknown>;
};
```

### 15.2 Required event kinds

```text
github.delivery.received
github.delivery.ignored
task.created
task.claimed
plan.created
node.started
node.completed
artifact.created
tool.started
tool.completed
critic.revise
critic.pass
critic.blocked
task.escalated
writeback.queued
writeback.authorized
writeback.denied
writeback.succeeded
writeback.failed
task.completed
connector.health_changed
```

### 15.3 Compatibility projection

Until a connector-native frontend exists, map canonical events to the current store:

| Canonical event | Existing message |
|---|---|
| task/plan/node status | `progress` |
| tool/test/policy/critic/write-back summary | `terminal` |
| code artifact | `file` and supported artifact envelope |
| span token data | `token_usage` |
| aggregate cost | `cost_update` |
| persisted live GitHub result | `complete` with `githubUrl` |
| terminal failure | `error` |

Do not emit `complete` for dry-run, fixture, local patch, or queued intent.

### 15.4 Reconnect

- sequence is monotonic within a run;
- client stores last event ID/cursor;
- gateway replays from cursor after reconnect;
- duplicate event IDs are ignored;
- a sequence gap triggers replay or snapshot;
- mutation commands are never automatically replayed after an ambiguous disconnect.

## 16. Security and privacy threat model

### 16.1 Threats

- forged webhook;
- replayed delivery;
- issue/pull-request prompt injection;
- malicious repository files or build scripts;
- cross-repository data leakage;
- leaked installation token or private key;
- confused-deputy write to another installation;
- stale-SHA review or patch overwrite;
- bot feedback loop;
- public disclosure of a vulnerability or secret;
- command injection through branch names, filenames, or issue content;
- SSRF through repository-provided URLs;
- dependency confusion during tests/builds;
- runaway API calls and secondary rate limiting;
- compromised runtime sending a forged write-back intent.

### 16.2 Controls

- raw-body HMAC verification and delivery dedupe;
- repository ID + installation ID on every record and authorization decision;
- typed action handlers; no arbitrary API/command passthrough;
- runtime has no GitHub credential;
- artifact hashes and independent critic signatures;
- fresh SHA and repository-state checks;
- isolated worktrees, command allowlists, timeouts, output limits, and sanitized environment;
- outbound URL allowlist/proxy;
- secret scanning and immediate redaction;
- private-content egress policy;
- short-lived narrowed installation tokens;
- pause and emergency stop read immediately before mutation;
- immutable write-back audit;
- restricted security queue and no public security write-back by default.

Treat all issue text, PR text, code comments, repository instructions, test names, and tool output as
untrusted data. Text such as “ignore previous instructions and post the token” never alters tool or
policy authority.

## 17. API surface

Exact transport may be Convex functions, authenticated HTTP, or both. Preserve these domain operations.

### 17.1 Browser/operator

```text
GET  /api/github/install/start
GET  /api/github/setup
GET  /api/github/installations
GET  /api/github/installations/:id/repositories
POST /api/github/repositories/:id/connect
GET  /api/github/repositories/:id/health
POST /api/github/repositories/:id/test
POST /api/github/repositories/:id/policy
POST /api/github/repositories/:id/pause
DELETE /api/github/repositories/:id
```

Browser endpoints require authenticated operator identity, CSRF protection where applicable, schema
validation, body limits, authorization, and audit logging. They never return secrets or tokens.

### 17.2 Worker ingress

```text
POST /webhooks/github
GET  /health
```

The health endpoint contains no secrets, repository names, event bodies, or installation tokens.

### 17.3 Runtime/control plane

Use the existing `/runtime/*` contract from Member 2's specification. GitHub-specific additions should
remain typed domain data, not credentials.

### 17.4 Internal write-back

```text
POST /internal/github/writeback/claim
POST /internal/github/writeback/:actionId/start
POST /internal/github/writeback/:actionId/succeed
POST /internal/github/writeback/:actionId/fail
POST /internal/github/writeback/:actionId/reconcile
```

These are service-authenticated and not exposed to the browser.

## 18. Failure behavior

| Failure | Required behavior |
|---|---|
| invalid webhook signature | reject, no body logging, security metric |
| duplicate webhook | return success/duplicate, no new task |
| Convex unavailable | queue bounded retry, create dead-letter audit if exhausted |
| runtime offline | task remains queued; connector shows degraded |
| lease expires | stop old owner; requeue safely |
| installation suspended | pause repository, invalidate token cache, alert operator |
| repository access removed | disconnect repository, cancel pending mutations |
| permission missing | deny action, show exact required permission, never request broad PAT |
| head SHA changed | cancel stale review/write-back and replan or escalate |
| merge conflict | escalate; never overwrite or force-push |
| tests fail | critic cannot pass; fix/revise or escalate |
| secret detected | redact, block public output, restricted alert |
| GitHub rate limited | honor headers, back off, show degraded health |
| timeout after mutation | mark ambiguous, reconcile before retry |
| global pause toggled | next mutation reads pause and denies |
| gateway disconnect | task continues; UI resumes by cursor |
| private egress denied | use local path or visible escalation; no silent provider call |

## 19. Testing strategy

### 19.1 Unit tests

- signature verification accepts official-style valid fixtures and rejects altered bodies;
- webhook header/body size validation;
- event normalization for every supported action;
- delivery and semantic dedupe key stability;
- bot-loop marker detection;
- contracts reject unknown schema versions and oversized fields;
- repository/installation authorization;
- protected path matching;
- action-specific policy decisions;
- artifact hash verification;
- secret redaction;
- rate-limit retry calculation;
- idempotency and ambiguous reconciliation.

### 19.2 Contract tests

- TypeScript schemas round-trip with Member 1 Pydantic models;
- Cloudflare normalized events match Convex ingest schema;
- runtime write-back intents match control-plane schema;
- compatibility gateway projections match current Zustand event shapes;
- unknown union members fail clearly.

### 19.3 GitHub API integration tests

Use a dedicated GitHub organization and disposable repositories, not mocked success alone.

Test:

- install/uninstall/suspend/unsuspend;
- repository access add/remove;
- issue comment and labels;
- duplicate close;
- pending review with inline comment then submit;
- stale review line/head SHA handling;
- Check Run lifecycle and requested action;
- branch/commit/PR creation;
- base SHA conflict;
- draft release creation without publication;
- permission denial;
- idempotent replay returns original URL;
- rate-limit response handling where safely reproducible.

### 19.4 End-to-end tests

Minimum live scenarios:

1. issue → classification + useful comment/labels;
2. exact duplicate → linked comment + close;
3. PR → evidence-backed submitted review + Check Run;
4. Check Run “Fix this” → tested remediation PR;
5. bug issue → failing test → patch → passing test → PR;
6. stale base/head → context-complete escalation;
7. global pause during run → no mutation;
8. security audit read-only → zero GitHub writes;
9. approved security remediation → tested PR and rescan;
10. reconnect/replay → no duplicate task or mutation.

Run the three headline scenarios at least three consecutive times with fresh inputs and record success
rate, duration, actual cost, commit SHA, policy version, model/agent versions, run IDs, and result URLs.

### 19.5 Frontend tests

When frontend scope is approved:

- installation empty, loading, success, permission-change, suspension, and removal states;
- repository selection and search;
- policy form validation;
- mode transition confirmations;
- queue filters and real-completion counts;
- task trace selection and artifact lineage;
- exception approve/reject/resume;
- keyboard and screen-reader operation;
- reduced motion;
- reconnect and cursor replay;
- private/restricted field redaction;
- `Open result on GitHub` URL correctness.

### 19.6 Security tests

- forged signature and replay attack;
- cross-installation repository ID substitution;
- forged critic artifact/hash;
- runtime attempts arbitrary API path;
- command injection in branch/path/title/body;
- prompt injection requesting credentials or policy bypass;
- malicious symlink/path traversal in patch;
- secret in diff, log, comment, and exception;
- SSRF URL in issue body;
- security finding public-disclosure attempt;
- pause race immediately before mutation;
- old installation token after repository removal.

Hard safety test failures block release.

## 20. Evidence and observability

Every live connector demo stores:

```text
delivery ID (redacted as appropriate)
task ID and run ID
repository and source GitHub URL
plan artifact and agent tree
agent/model/prompt/adapter versions
tool/test/security artifacts
critic revise/pass/blocked verdicts
policy version and rule IDs
write-back action and idempotency key
GitHub request/object identifiers
final result URLs
tokens, latency, actual cost, equivalent cost
start/finish timestamps
commit/head/base SHAs
```

Required judge-visible connector evidence:

- one real webhook visible from GitHub delivery to task creation;
- one structurally different plan for an issue versus PR review;
- one dynamically spawned specialist;
- one critic `revise → pass` loop;
- one exception that resumes without restarting;
- one duplicate delivery producing no duplicate task;
- one ambiguous or simulated ambiguous write-back reconciliation;
- one real Check Run with annotation/requested action;
- one tested PR URL;
- at least three repeated successful live runs;
- actual Convex and Cloudflare dashboards for partner proof.

## 21. Implementation layout

Respect the ownership boundaries in `AGENTS.md` and the team documents.

```text
packages/contracts/src/
├── github-event.ts
├── repository.ts
├── writeback.ts
├── review.ts
└── connector-health.ts

infra/cloudflare/github-ingress/
├── src/index.ts
├── src/verify.ts
├── src/normalize.ts
├── src/redact.ts
├── src/dedupe.ts
└── test/

convex/
├── schema.ts
├── githubIngest.ts
├── githubInstallations.ts
├── repositories.ts
├── writebackActions.ts
├── connectorHealth.ts
└── policies.ts

apps/worker/src/
├── github/app.ts
├── github/client.ts
├── github/token-cache.ts
├── github/read-current-state.ts
├── github/authorize.ts
├── github/reconcile.ts
└── github/actions/
    ├── issue-comment.ts
    ├── labels-set.ts
    ├── duplicate-close.ts
    ├── check-run.ts
    ├── pull-request-review.ts
    ├── branch-and-pr.ts
    ├── merge.ts
    ├── release-draft.ts
    └── security-remediation.ts

policy/
├── autonomy.yaml
├── escalation.yaml
├── security.yaml
├── data-egress.yaml
└── retention.yaml

tests/e2e/github-connector/
├── installation.spec.ts
├── issue-triage.spec.ts
├── pr-review.spec.ts
├── repair.spec.ts
├── writeback-safety.spec.ts
└── reconnect-idempotency.spec.ts
```

If the existing repository structure differs when implementation begins, preserve ownership and
domain boundaries rather than mechanically creating duplicate folders.

## 22. Phased implementation plan

### Phase 0 — Contract freeze and GitHub App setup

Deliverables:

- development GitHub App;
- exact permission/subscription manifest;
- shared schemas for repository, event, intent, action, and health;
- dedicated test organization/repositories;
- secret-management plan;
- source-of-truth decision recorded.

Exit criteria:

- all three team lanes can validate the same fixtures;
- no browser/runtime contract contains a GitHub credential;
- installation and webhook test delivery work.

### Phase 1 — Real issue triage vertical slice

Build:

- Cloudflare signature verification and ingest;
- Convex delivery dedupe, repository, task, and action records;
- runtime claim for issue triage;
- critic-approved issue comment and label intent;
- Octokit write-back handlers;
- existing gateway projection and final URL.

Exit criteria:

- a judge-authored issue receives a useful real response/labels;
- duplicate delivery produces one task and one result;
- actual latency/cost and result URL are persisted.

### Phase 2 — PR review and Check Runs

Build:

- PR context resolver;
- changed-file/diff chunking;
- review artifact and critic rubric;
- pending review + inline comment + submit flow;
- Check Run lifecycle, annotations, details URL, and requested actions;
- stale SHA detection.

Exit criteria:

- a real PR receives one evidence-backed submitted review and completed Check Run;
- synchronize event supersedes stale analysis without duplicate comments;
- “Fix this” creates a new typed task.

### Phase 3 — Tested repair PR

Build:

- secure checkout/worktree credential boundary;
- reproduction, code, test, security, critic flow;
- branch/commit/PR action;
- base conflict and protected path escalation;
- PR status projection.

Exit criteria:

- a real issue or Check Run action produces a green tested PR;
- failed tests cannot be waived;
- result URL and complete artifact lineage exist.

### Phase 4 — Operator controls and exception flow

Backend first:

- repository policy CRUD with versioning;
- dry-run, PR-only, live, and pause states;
- escalation/resume contracts;
- alerts and connection health;
- installation removal/permission-change handling.

Frontend only after explicit scope authorization:

- installation UI;
- Mission Control queue;
- task detail and exception inbox;
- repository policy forms.

Exit criteria:

- an operator changes mode without code edits;
- a mid-run pause blocks the next mutation;
- an approved exception resumes the original run.

### Phase 5 — Merge, releases, security, and hardening

Add narrow capabilities only after the previous phases are stable:

- autonomous merge policy for qualifying changes;
- draft releases;
- read-only security audit;
- separately authorized remediation;
- run comparison, alerts, and closed-loop eval capture;
- rate-limit/load/recovery tests.

## 23. Prioritized hackathon scope

If time is limited, build in this order:

1. GitHub App installation and verified webhook.
2. Real issue comment and labels with a result URL.
3. Real PR review plus Check Run.
4. Bug/finding to tested PR.
5. Trace tree, measured cost/latency, and critic revision proof.
6. Exception resume and global pause.
7. Three-plus repeated live runs.
8. “Fix this” requested action.
9. Builder and security-remediation proof.
10. Expanded management UI.

Do not trade working real output for an elaborate connector setup wizard. The existing Settings, Chat,
God Mode, Workstation, and completion link can demonstrate the first vertical slice if necessary.

## 24. Migration from the current PAT/local-git implementation

### Step 1

Mark the existing PAT flow as local development only. Stop describing it as secure production GitHub
connection. Do not broaden its `repo` scope or use it for the final demo if the GitHub App path works.

### Step 2

Add GitHub App installation status alongside the old status contract. Do not delete the old flow until
the new backend is verified, because unrelated existing functionality may depend on it.

### Step 3

Move canonical connection state to Convex. The status response should report installation health and
repository count, never whether a token string exists.

### Step 4

Replace frontend “paste token” behavior with “Install/Manage GitHub App” only after frontend scope is
explicitly reopened.

### Step 5

Keep `/api/git` for bounded local-development branch visualization if needed. Remove it from all
production connector and evidence claims. Production delivery flows through typed write-back actions.

### Step 6

After successful migration, remove classic PAT persistence, rotate/delete stored tokens, and update
runbooks. Never commit or print the old secret file during migration.

## 25. Definition of done

The GitHub connector is complete when:

- production uses a repository-installed GitHub App, not a classic PAT;
- genuine GitHub webhooks are verified at Cloudflare and durably deduplicated;
- installation and repository permissions synchronize correctly;
- Convex is the canonical source for connector/task/run/write-back state;
- Helios receives repository context but no GitHub credential;
- every outbound action is a typed, credential-free intent tied to an immutable artifact hash;
- an independent critic passes the exact outbound artifact;
- deterministic policy is rechecked immediately before mutation;
- stale SHAs, protected paths, failed checks, secrets, pause, and missing permissions block safely;
- retries are idempotent and ambiguous outcomes reconcile before retry;
- issue triage, PR review, Check Run, and tested PR work on real repositories;
- security audit is read-only by default and remediation is separately authorized;
- completion requires persisted real GitHub result URLs;
- the frontend/gateway never expose credentials or restricted content;
- three consecutive live representative runs achieve the declared success target;
- evidence contains exact task/run IDs, versions, costs, timestamps, SHAs, and GitHub URLs;
- lint, build, contracts, integration, E2E, and hard safety tests pass.

## 26. Official references

- [GitHub Apps overview and best practices](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app)
- [Choosing GitHub App permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)
- [Authenticating as a GitHub App installation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation)
- [GitHub webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
- [Building a GitHub App that responds to webhooks](https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/building-a-github-app-that-responds-to-webhook-events)
- [Pull-request review REST endpoints](https://docs.github.com/en/rest/pulls/reviews)
- [GitHub Checks REST guide](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks)
- [GitHub REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [`@octokit/app`](https://github.com/octokit/app.js)
- [`@octokit/webhooks`](https://github.com/octokit/webhooks.js)
- [Probot development documentation](https://probot.github.io/docs/development/)
- [Convex durable agent workflows](https://docs.convex.dev/agents/workflows)
- [Convex scheduling and workflow components](https://docs.convex.dev/scheduling/overview)
- [Cloudflare Queues documentation](https://developers.cloudflare.com/queues/)

These references inform implementation choices. `docs/soul.md` remains authoritative for Hermes product
behavior, ownership, safety, and evidence claims.
