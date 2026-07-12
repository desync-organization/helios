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

Local APIs bind to `127.0.0.1` by default. Mutations require `HELIOS_LOCAL_API_TOKEN`, and CORS
permits only `HELIOS_ALLOWED_ORIGIN`.

