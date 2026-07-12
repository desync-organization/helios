"""Create and verify immutable dataset manifests."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from hermes_training.hashing import sha256_file, sha256_value
from hermes_training.models import DatasetManifest, DatasetRecord


def build_manifest(
    *,
    manifest_id: str,
    dataset_path: Path,
    records: list[DatasetRecord],
    config_sha256: str,
    created_at: datetime | None = None,
) -> DatasetManifest:
    if not records:
        raise ValueError("cannot manifest an empty dataset")
    split_counts = Counter(record.split for record in records)
    mode_counts = Counter(record.mode for record in records)
    payload = {
        "schemaVersion": "1.0",
        "manifestId": manifest_id,
        "createdAt": created_at or datetime.now(UTC),
        "datasetPath": dataset_path.as_posix(),
        "datasetSha256": sha256_file(dataset_path),
        "recordCount": len(records),
        "splitCounts": {
            "train": split_counts.get("train", 0),
            "dev": split_counts.get("dev", 0),
            "test": split_counts.get("test", 0),
        },
        "modeCounts": {
            "maintain": mode_counts.get("maintain", 0),
            "build": mode_counts.get("build", 0),
            "security_audit": mode_counts.get("security_audit", 0),
        },
        "recordHashes": [record.content_sha256 for record in records],
        "gauntletCaseHashes": [],
        "configSha256": config_sha256,
        "manifestSha256": "0" * 64,
    }
    provisional = DatasetManifest.model_validate(payload)
    canonical = provisional.model_dump(
        mode="json",
        by_alias=True,
        exclude={"manifest_sha256"},
    )
    payload["manifestSha256"] = sha256_value(canonical)
    return DatasetManifest.model_validate(payload)


def verify_manifest(manifest: DatasetManifest, dataset_path: Path) -> None:
    if sha256_file(dataset_path) != manifest.dataset_sha256:
        raise ValueError("dataset file hash does not match manifest")
    payload = manifest.model_dump(mode="json", by_alias=True, exclude={"manifest_sha256"})
    if sha256_value(payload) != manifest.manifest_sha256:
        raise ValueError("manifestSha256 does not match manifest contents")
