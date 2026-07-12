# Helios Runtime

The credential-free, on-device execution plane for Hermes. One planner/scheduler/artifact kernel
supports GitHub maintenance, bounded product building, and defensive repository security audits.

## Setup

Requires Python 3.12+.

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[test]"
python -m helios.models.bootstrap
pytest tests -q
python -m helios.demo.seed_runtime
python -m helios.main
```

The runtime never accepts GitHub or provider credentials. It returns schema-versioned,
idempotent write-back intents to the control plane. Without `CONVEX_HTTP_URL`, it uses the
in-memory control-plane adapter for independent development.

## Agent reservoir

`agents/baseline.yaml` is the single catalog used by the head planner, scheduler and `/roles` API.
It includes active agents plus spawnable templates. The planner receives full capabilities, models,
tools, modes, budgets, artifact types, adapter identity and current lifecycle state. A spawned agent
is policy-checked, installed into the scheduler, emitted as an `agent_spawned` event, and persisted in
`workspace/agent-reservoir.json` before delegation. Every output passes deterministic head validation
and then the independent critic gate.

## Gemma web SLMs

The reservoir includes three narrow Gemma 3 1B templates: `html-slm`, `css-slm`, and
`javascript-slm`. Their QLoRA/distillation package is in `training/`. No untrained adapter is loaded:
model mode requires a hash-bound promotion manifest and exact Gemma base before spawning.

After training and promotion, validate the dedicated endpoints without starting them:

```bash
python -m helios.models.slm
```

Then start all three localhost llama.cpp processes with their separately verified adapters:

```bash
python -m helios.models.slm --start
```

Set `HELIOS_INFERENCE_MODE=model` only after preflight reports the required model services ready.

Local APIs bind to `127.0.0.1` by default. Mutations require `HELIOS_LOCAL_API_TOKEN`, and CORS
permits only `HELIOS_ALLOWED_ORIGIN`.
