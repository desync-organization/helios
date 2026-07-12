"""Generate an evidence-linked model card from a completed, checksummed run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hermes_training.run_artifacts import verify_checksums


def generate_model_card(run_root: Path) -> Path:
    verify_checksums(run_root)
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "complete":
        raise ValueError("model cards require a completed training run")
    provenance = json.loads((run_root / "provenance.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_root / "metrics.json").read_text(encoding="utf-8"))
    card = f"""# {provenance['runId']}

## Intended Use

This adapter targets reviewed Hermes maintainer triage, reply, and documentation behavior. It grants
no tools or permissions and must not be attached to the independent Critic.

## Reproducibility

- Base model: `{provenance['baseModelId']}` at `{provenance['baseModelRevision']}`
- Base hash: `{provenance['baseModelSha256']}`
- Tokenizer hash: `{provenance['tokenizerSha256']}`
- Dataset manifest: `{provenance['datasetManifestSha256']}`
- Training config: `{provenance['configSha256']}`

## Training Metrics

```json
{json.dumps(metrics, indent=2, sort_keys=True)}
```

## Limitations and Promotion

Training completion is not promotion. The adapter remains an experiment until identical held-out
base-versus-adapter evaluations, safety gates, latency/memory checks, loader compatibility, three
stable runs, atomic activation, and rollback all pass.
"""
    output = run_root / "MODEL_CARD.md"
    output.write_text(card, encoding="utf-8", newline="\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(generate_model_card(args.run.resolve()))


if __name__ == "__main__":
    main()
