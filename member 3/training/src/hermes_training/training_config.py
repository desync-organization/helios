"""Strict, reproducible LoRA/QLoRA configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QuantizationConfig(FrozenModel):
    bits: Literal[4] = 4
    quant_type: Literal["nf4"] = "nf4"
    double_quant: bool = True


class LoraSettings(FrozenModel):
    rank: int = Field(ge=1, le=256)
    alpha: int = Field(ge=1, le=512)
    dropout: float = Field(ge=0, lt=1)
    target_modules: list[str] = Field(min_length=1)


class TrainingSettings(FrozenModel):
    epochs: float = Field(gt=0, le=10)
    learning_rate: float = Field(gt=0, le=0.01)
    max_length: int = Field(ge=128, le=32768)
    batch_size: int = Field(ge=1)
    gradient_accumulation_steps: int = Field(ge=1)
    warmup_ratio: float = Field(ge=0, lt=1)
    weight_decay: float = Field(ge=0, le=1)
    logging_steps: int = Field(ge=1)
    seed: int
    packing: bool
    assistant_only_loss: bool


class TrainingConfig(FrozenModel):
    schema_version: str
    run_name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]+$")
    base_model_id: str = Field(min_length=3)
    base_model_revision: str = Field(min_length=7)
    base_model_sha256: str
    tokenizer_sha256: str
    dataset_manifest: Path
    output_root: Path
    method: Literal["qlora", "lora"]
    compute_dtype: Literal["bf16", "fp16"]
    quantization: QuantizationConfig | None
    lora: LoraSettings
    training: TrainingSettings

    @model_validator(mode="after")
    def reject_placeholders_and_unsafe_combinations(self) -> TrainingConfig:
        pin_fields = (
            self.base_model_revision,
            self.base_model_sha256,
            self.tokenizer_sha256,
        )
        if any("<" in value or ">" in value for value in pin_fields):
            raise ValueError("base revision and hashes must be replaced with verified values")
        if self.method == "qlora" and self.quantization is None:
            raise ValueError("QLoRA requires a 4-bit quantization block")
        if self.method == "lora" and self.quantization is not None:
            raise ValueError("ordinary LoRA must not include a quantization block")
        return self


def load_training_config(path: Path) -> tuple[TrainingConfig, bytes]:
    raw = path.read_bytes()
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError("training config must contain a YAML object")
    return TrainingConfig.model_validate(value), raw
