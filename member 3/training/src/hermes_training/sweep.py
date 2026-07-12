"""Expand a reviewed sweep matrix into immutable training configurations."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Any

import yaml

from hermes_training.io import write_json_atomic
from hermes_training.training_config import TrainingConfig


def expand_sweep(base: dict[str, Any], matrix: dict[str, list[Any]]) -> list[TrainingConfig]:
    allowed = {
        "lora.rank",
        "lora.alpha",
        "training.learning_rate",
        "training.packing",
        "training.seed",
    }
    unknown = set(matrix) - allowed
    if unknown:
        raise ValueError(f"unsupported sweep keys: {', '.join(sorted(unknown))}")
    variants: list[TrainingConfig] = []
    keys = sorted(matrix)
    for values in itertools.product(*(matrix[key] for key in keys)):
        candidate = yaml.safe_load(yaml.safe_dump(base))
        suffix: list[str] = []
        for key, value in zip(keys, values, strict=True):
            parent, field = key.split(".", maxsplit=1)
            candidate[parent][field] = value
            suffix.append(f"{field}-{str(value).lower()}")
        candidate["run_name"] = f"{base['run_name']}-{'-'.join(suffix)}"
        variants.append(TrainingConfig.model_validate(candidate))
    return variants


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    variants = expand_sweep(raw["base"], raw["matrix"])
    args.output.mkdir(parents=True, exist_ok=True)
    for variant in variants:
        write_json_atomic(
            args.output / f"{variant.run_name}.json",
            variant.model_dump(mode="json"),
        )
    print(f"wrote {len(variants)} configurations")


if __name__ == "__main__":
    main()
