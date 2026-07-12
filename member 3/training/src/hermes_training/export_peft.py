"""Verify and inventory the PEFT adapter produced by a completed training run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hermes_training.hashing import sha256_file
from hermes_training.io import write_json_atomic
from hermes_training.run_artifacts import verify_checksums


def export_peft(run_root: Path) -> Path:
    verify_checksums(run_root)
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "complete":
        raise ValueError("only a completed training run can be exported")
    adapter = run_root / "adapter"
    config = adapter / "adapter_config.json"
    weights = adapter / "adapter_model.safetensors"
    if not config.is_file() or not weights.is_file():
        raise FileNotFoundError("completed run lacks PEFT config or safetensors weights")
    output = run_root / "peft-export.json"
    write_json_atomic(
        output,
        {
            "format": "peft-safetensors",
            "adapterConfigSha256": sha256_file(config),
            "adapterSha256": sha256_file(weights),
            "adapterPath": str(adapter),
        },
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(export_peft(args.run.resolve()))


if __name__ == "__main__":
    main()
