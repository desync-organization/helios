from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from hermes_training.dedupe import find_duplicates
from hermes_training.io import write_jsonl_atomic
from hermes_training.models import DatasetPayload, DatasetRecord, ScanResult
from hermes_training.prepare import prepare_dataset
from hermes_training.redact import redact_text, scan_text
from hermes_training.split import apply_splits
from hermes_training.validate import validate_dataset
from pydantic import ValidationError


def payload(**updates: object) -> DatasetPayload:
    values: dict[str, object] = {
        "exampleId": "maintain-001",
        "mode": "maintain",
        "taskType": "classify",
        "repositoryGroup": "example/widgets",
        "threadId": "issue-1",
        "sourceUrl": "https://example.invalid/issues/1",
        "sourceCommit": "a" * 40,
        "license": "MIT",
        "provenance": "team-authored fixture",
        "collectedAt": datetime(2026, 7, 12, tzinfo=UTC),
        "reviewer": "human-reviewer",
        "reviewStatus": "approved",
        "input": {"title": "Button fails on submit"},
        "expectedArtifactType": "classification",
        "target": {"class": "bug", "priority": "p2"},
        "policyContext": {"allowedLabels": ["bug"]},
        "safetyTags": [],
        "piiSecretScan": ScanResult(status="clean", scannerVersion="1.0.0"),
        "split": None,
    }
    values.update(updates)
    return DatasetPayload.model_validate(values)


def test_record_hash_is_verified() -> None:
    record = DatasetRecord.from_payload(payload())
    assert len(record.content_sha256) == 64
    with pytest.raises(ValidationError, match="contentSha256"):
        DatasetRecord.model_validate(
            {**record.model_dump(mode="json", by_alias=True), "contentSha256": "0" * 64}
        )


def test_secret_scanner_redacts_without_returning_secret() -> None:
    secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    findings = scan_text(f"token={secret}")
    redacted, _ = redact_text(f"token={secret}")
    assert findings[0].kind == "github_token"
    assert secret not in repr(findings)
    assert secret not in redacted
    assert "REDACTED:GITHUB_TOKEN" in redacted


def test_grouped_split_keeps_thread_together() -> None:
    records = [payload(exampleId="one"), payload(exampleId="two")]
    split_records = apply_splits(records, seed=3407)
    assert split_records[0].split == split_records[1].split


def test_near_duplicate_detection_marks_cross_split() -> None:
    left = payload(exampleId="left", split="train")
    right = payload(exampleId="right", split="test")
    duplicates = find_duplicates([left, right])
    assert len(duplicates) == 1
    assert duplicates[0].crosses_split is True


def test_unreviewed_record_is_rejected() -> None:
    with pytest.raises(ValidationError):
        payload(reviewStatus="pending-review")


def test_prepare_and_validate_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    output = tmp_path / "processed.jsonl"
    manifest = tmp_path / "manifest.json"
    config = tmp_path / "config.yaml"
    raw = payload().model_dump(mode="json", by_alias=True, exclude_none=False)
    write_jsonl_atomic(source, [raw])
    config.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "source": str(source),
                "output": str(output),
                "manifest": str(manifest),
                "redaction_mode": "block",
                "dedupe_threshold": 0.94,
                "split_seed": 3407,
                "split_ratios": {"train": 0.8, "dev": 0.1, "test": 0.1},
            }
        ),
        encoding="utf-8",
    )
    prepare_dataset(config, workspace=tmp_path)
    assert validate_dataset(manifest, workspace=tmp_path) == 1
