"""Validate dataset hashes, provenance, split isolation, redaction, and manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hermes_training.dedupe import find_duplicates
from hermes_training.io import read_jsonl
from hermes_training.manifest import verify_manifest
from hermes_training.models import DatasetManifest, DatasetRecord
from hermes_training.redact import scan_value


def validate_dataset(manifest_path: Path, *, workspace: Path) -> int:
    manifest = DatasetManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
    dataset_path = Path(manifest.dataset_path)
    if not dataset_path.is_absolute():
        dataset_path = workspace / dataset_path
    verify_manifest(manifest, dataset_path)
    records = [DatasetRecord.model_validate(item) for item in read_jsonl(dataset_path)]
    if len(records) != manifest.record_count:
        raise ValueError("record count does not match manifest")
    if [record.content_sha256 for record in records] != manifest.record_hashes:
        raise ValueError("record hash order does not match manifest")
    for record in records:
        findings = scan_value(
            {"input": record.input, "target": record.target, "policy": record.policy_context}
        )
        if findings:
            raise ValueError(f"record {record.example_id} contains unredacted sensitive content")
    cross_split = [pair for pair in find_duplicates(records) if pair.crosses_split]
    if cross_split:
        raise ValueError("near-duplicate content crosses dataset splits")
    gauntlet_overlap = set(manifest.record_hashes) & set(manifest.gauntlet_case_hashes)
    if gauntlet_overlap:
        raise ValueError("training dataset overlaps held-out Gauntlet cases")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    count = validate_dataset(args.manifest, workspace=args.workspace.resolve())
    print(f"validated {count} records")


if __name__ == "__main__":
    main()

