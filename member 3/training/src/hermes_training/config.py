"""Configuration loading with paths resolved relative to the workspace."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SplitRatios(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train: float = Field(gt=0, lt=1)
    dev: float = Field(ge=0, lt=1)
    test: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def sum_to_one(self) -> SplitRatios:
        if abs(self.train + self.dev + self.test - 1.0) > 1e-9:
            raise ValueError("split ratios must sum to 1.0")
        return self


class DatasetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    source: Path
    output: Path
    manifest: Path
    redaction_mode: str = Field(pattern=r"^(block|redact)$")
    dedupe_threshold: float = Field(ge=0.8, le=1.0)
    split_seed: int
    split_ratios: SplitRatios


def load_dataset_config(path: Path) -> tuple[DatasetConfig, bytes]:
    raw = path.read_bytes()
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError("dataset config must contain a YAML object")
    return DatasetConfig.model_validate(value), raw


def resolve_workspace_path(workspace: Path, configured: Path) -> Path:
    return configured if configured.is_absolute() else workspace / configured
