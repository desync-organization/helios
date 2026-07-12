from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: value.split("_")[0] + "".join(
        part.capitalize() for part in value.split("_")[1:]
    ), populate_by_name=True, extra="forbid")


class ModelSpec(StrictModel):
    student_id: str
    student_revision: str
    teacher_id: str
    teacher_revision: str
    local_files_only: bool = True
    trust_remote_code: bool = False


class AdapterSpec(StrictModel):
    adapter_id: str
    adapter_version: str
    method: Literal["lora", "qlora"]
    rank: int = Field(ge=1, le=256)
    alpha: float = Field(gt=0)
    dropout: float = Field(ge=0, lt=1)
    target_modules: list[str] = Field(min_length=1)
    quantization: Literal["none", "nf4"]

    @model_validator(mode="after")
    def method_matches_quantization(self) -> "AdapterSpec":
        if self.method == "qlora" and self.quantization != "nf4":
            raise ValueError("QLoRA requires nf4 quantization")
        if self.method == "lora" and self.quantization != "none":
            raise ValueError("LoRA requires quantization=none")
        return self


class DataSpec(StrictModel):
    train_path: str
    validation_path: str
    max_sequence_length: int = Field(ge=256, le=32768)
    require_teacher_trace: bool = True


class TrainingSpec(StrictModel):
    output_dir: str
    seed: int = 42
    epochs: float = Field(gt=0)
    learning_rate: float = Field(gt=0)
    warmup_ratio: float = Field(ge=0, lt=1)
    per_device_train_batch_size: int = Field(ge=1)
    gradient_accumulation_steps: int = Field(ge=1)
    gradient_checkpointing: bool = True
    bf16: bool = True
    save_steps: int = Field(ge=1)
    eval_steps: int = Field(ge=1)
    logging_steps: int = Field(ge=1)


class SpecialistSpec(StrictModel):
    schema_version: Literal["1.0"]
    role: Literal["html-slm", "css-slm", "javascript-slm"]
    capability: str
    output_contract: list[str] = Field(min_length=1)
    forbidden: list[str] = Field(min_length=1)
    model: ModelSpec
    adapter: AdapterSpec
    data: DataSpec
    training: TrainingSpec


def load_spec(path: Path) -> SpecialistSpec:
    if not path.is_file():
        raise FileNotFoundError(f"specialist spec does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SpecialistSpec.model_validate(payload)


def require_pinned_models(spec: SpecialistSpec) -> None:
    revisions = (spec.model.student_revision, spec.model.teacher_revision)
    if any(not value or value.startswith("REPLACE_") for value in revisions):
        raise ValueError("student and teacher revisions must be replaced with reviewed immutable commits")
