# Helios

Helios is a local prompt-to-site application built with Next.js 16, FastAPI, and Ollama.

## Run locally

```bash
bun dev
```

That single command:

- installs the locked frontend dependencies when missing;
- creates/synchronizes the Python runtime environment when missing;
- starts Ollama when needed and pulls the configured head and Gemma SLM base models when missing;
- provisions distinct HTML, CSS, and JavaScript SLM identities from reviewed role definitions;
- starts the Helios runtime only after the head and all three SLMs are ready;
- starts Next.js on the first available port from `3000` and prints the exact URL;
- stops the processes it owns when you press `Ctrl+C`.

Prerequisites are Bun, Python 3.12+ (or `uv`), and Ollama. The head defaults to
`llama3.2:latest`; override it with `HELIOS_OLLAMA_SITE_MODEL`. The specialists share the small
`gemma3:4b` base weights but have distinct `helios-html-slm`, `helios-css-slm`, and
`helios-javascript-slm` identities and fixed role prompts. Set `HELIOS_OLLAMA_SITE_DIGEST` to enforce
an exact reviewed head digest. Each task is decomposed by the head, authored by all three SLMs,
integrated deterministically, and returned to the head for a whole-project review. The standalone
command never starts Convex, the Worker, or the compatibility gateway because they are not part of
the direct prompt-to-site path.

These default SLMs are prompt-specialized local Gemma models, not promoted LoRA adapters. The
separate llama.cpp adapter pipeline remains fail-closed until its training, evaluation, manifests,
and hashes are promoted.

## Bounded specialist handoffs

The head and site specialists can attach typed handoff messages to their normal plan, file, review,
and revision responses. The only valid tags are `@head`, `@html`, `@css`, and `@javascript`.
Helios records the authenticated sender and routes the tag; models cannot choose or impersonate the
sender recorded in the transcript.

Handoffs follow the same forward-only execution graph as the files:

- the head can message the HTML, CSS, and JavaScript SLMs after planning and during review;
- the HTML SLM can message the CSS and JavaScript SLMs;
- the CSS SLM can message the JavaScript SLM;
- every specialist can message `@head` with a question, risk, or cross-file concern;
- a concern that would require changing an already-produced or differently owned file goes through
  `@head`, which can route a typed review issue to that file's owner.

The head plan can emit at most three messages, each specialist response can emit at most two, and a
head review can route at most twelve typed issues while still remaining inside the task-wide limit
of sixteen recorded messages. Every specialist structured response includes a `messages` array;
assignment-required handoffs must be present, while the array may be empty when no coordination is
useful. Messages are delivered only at predetermined orchestration
boundaries; they never trigger a dynamic model-call loop, carry replacement file content, or let one
specialist edit another specialist's file. The head still has one bounded revision round, and
deterministic validation remains the final authority over the integrated output.

The WebSocket streams each accepted handoff as a structured `agent_message` event and as a
compatibility activity line such as `[HTML] @css — Preserve the navigation class names.` The final
result includes the same ordered `agentMessages` transcript. This is an observable typed handoff
protocol, not an unbounded or hidden multi-agent chat.

For frontend-only development, use `bun run dev:web`. The legacy control-plane integration stack is
still available through `bun run dev:control-plane`.

## Verify a production build

```bash
bun run build
```

The project includes server-side API routes. For a Tauri-specific static export that omits those routes, set `TAURI_STATIC_EXPORT=true` when building.
