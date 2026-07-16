from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["html-slm", "css-slm", "javascript-slm"]


class TeacherTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(alias="modelId")
    model_revision: str = Field(alias="modelRevision")
    response_sha256: str = Field(alias="responseSha256", pattern=r"^[a-f0-9]{64}$")


class DatasetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    example_id: str = Field(alias="exampleId", min_length=1)
    role: Role
    split: Literal["train", "validation", "test"]
    instruction: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    response: str = Field(min_length=1)
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)
    consent: Literal["synthetic", "licensed", "owned"]
    teacher: TeacherTrace | None = None


class DatasetValidationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[DatasetRecord]:
    records: list[DatasetRecord] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            try:
                records.append(DatasetRecord.model_validate_json(raw))
            except Exception as exc:
                raise DatasetValidationError(f"{path}:{line_number}: {exc}") from exc
    if not records:
        raise DatasetValidationError(f"dataset is empty: {path}")
    return records


def _content_errors(record: DatasetRecord) -> list[str]:
    output = record.response
    lowered = output.lower()
    errors: list[str] = []
    if record.role == "html-slm":
        if (
            "<script" in lowered
            or "<style" in lowered
            or re.search(r"\son\w+\s*=", lowered)
        ):
            errors.append(
                "HTML output must not contain scripts, styles, or inline event handlers"
            )
        if not re.search(r"<[a-z][^>]*>", lowered):
            errors.append("HTML output must contain markup")
    elif record.role == "css-slm":
        if "<style" in lowered or "</" in lowered or "javascript:" in lowered:
            errors.append(
                "CSS output must be standalone CSS without markup or javascript URLs"
            )
        if "{" not in output or "}" not in output:
            errors.append("CSS output must contain at least one rule")
    else:
        forbidden = ("eval(", "new function(", "document.write(", "javascript:")
        if any(item in lowered for item in forbidden):
            errors.append(
                "JavaScript output contains a forbidden dynamic-code or document-write primitive"
            )
        if "<script" in lowered:
            errors.append("JavaScript output must not contain script tags")
    return errors


def validate_records(
    records: Iterable[DatasetRecord],
    *,
    expected_role: Role | None = None,
    expected_split: str | None = None,
    require_teacher: bool = False,
    expected_teacher_id: str | None = None,
    expected_teacher_revision: str | None = None,
) -> list[DatasetRecord]:
    materialized = list(records)
    seen: set[str] = set()
    failures: list[str] = []
    for record in materialized:
        if record.example_id in seen:
            failures.append(f"{record.example_id}: duplicate exampleId")
        seen.add(record.example_id)
        if expected_role and record.role != expected_role:
            failures.append(
                f"{record.example_id}: expected role {expected_role}, got {record.role}"
            )
        if expected_split and record.split != expected_split:
            failures.append(
                f"{record.example_id}: expected split {expected_split}, got {record.split}"
            )
        if require_teacher and record.teacher is None:
            failures.append(f"{record.example_id}: teacher trace is required")
        if (
            record.teacher
            and expected_teacher_id
            and record.teacher.model_id != expected_teacher_id
        ):
            failures.append(
                f"{record.example_id}: teacher modelId does not match the specification"
            )
        if (
            record.teacher
            and expected_teacher_revision
            and record.teacher.model_revision != expected_teacher_revision
        ):
            failures.append(
                f"{record.example_id}: teacher modelRevision does not match the specification"
            )
        if (
            record.teacher
            and hashlib.sha256(record.response.encode("utf-8")).hexdigest()
            != record.teacher.response_sha256
        ):
            failures.append(
                f"{record.example_id}: teacher response hash does not match response"
            )
        failures.extend(
            f"{record.example_id}: {message}" for message in _content_errors(record)
        )
    if failures:
        raise DatasetValidationError("\n".join(failures))
    return materialized


def validate_pair(
    train_path: Path,
    validation_path: Path,
    *,
    role: Role,
    require_teacher: bool,
    expected_teacher_id: str | None = None,
    expected_teacher_revision: str | None = None,
) -> tuple[list[DatasetRecord], list[DatasetRecord]]:
    train = validate_records(
        read_jsonl(train_path),
        expected_role=role,
        expected_split="train",
        require_teacher=require_teacher,
        expected_teacher_id=expected_teacher_id,
        expected_teacher_revision=expected_teacher_revision,
    )
    validation = validate_records(
        read_jsonl(validation_path),
        expected_role=role,
        expected_split="validation",
        require_teacher=require_teacher,
        expected_teacher_id=expected_teacher_id,
        expected_teacher_revision=expected_teacher_revision,
    )
    overlap = {item.example_id for item in train} & {
        item.example_id for item in validation
    }
    content_overlap = {
        hashlib.sha256(
            (item.instruction + "\0" + item.response).encode("utf-8")
        ).hexdigest()
        for item in train
    } & {
        hashlib.sha256(
            (item.instruction + "\0" + item.response).encode("utf-8")
        ).hexdigest()
        for item in validation
    }
    if overlap or content_overlap:
        raise DatasetValidationError("train and validation datasets overlap")
    return train, validation


def write_manifest(paths: Iterable[Path], destination: Path) -> dict[str, Any]:
    entries = []
    totals: Counter[str] = Counter()
    for path in paths:
        records = read_jsonl(path)
        totals.update(item.split for item in records)
        entries.append(
            {"path": str(path), "sha256": sha256_file(path), "records": len(records)}
        )
    payload = {
        "schemaVersion": "1.0",
        "files": entries,
        "countsBySplit": dict(sorted(totals.items())),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
