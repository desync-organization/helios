# Hermes Member 3 Workspace

This isolated workspace implements Team Member 3's model-quality and proof lane without modifying the
frozen frontend or another member's owned paths. It contains governed dataset preparation, reproducible
LoRA/QLoRA tooling, deterministic multi-mode evaluation, the WebSocket compatibility gateway,
benchmarks, acceptance tests, evidence templates, and operator runbooks.

## Local setup

```powershell
cd "member 3"
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check .
```

Install the optional `training` dependency group only on a compatible training machine. Large model
weights, checkpoints, generated reports, and adapters stay outside Git; checked manifests and hashes
remain reviewable. This repository never treats fixtures, dry runs, or rehearsals as live completion.

