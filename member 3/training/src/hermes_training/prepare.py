"""Normalize, scan, group-split, deduplicate, and manifest reviewed records."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

from hermes_training.config import load_dataset_config, resolve_workspace_path
from hermes_training.dedupe import find_duplicates
from hermes_training.io import read_jsonl, write_json_atomic, write_jsonl_atomic
from hermes_training.manifest import build_manifest
from hermes_training.models import DatasetPayload, DatasetRecord, ScanResult
from hermes_training.redact import SCANNER_VERSION, redact_text, scan_value
from hermes_training.split import apply_splits


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)[0]
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _scan_and_normalize(payload: DatasetPayload, *, redaction_mode: str) -> DatasetPayload:
    protected = {
        "input": payload.input,
        "target": payload.target,
        "policyContext": payload.policy_context,
    }
    findings = scan_value(protected)
    if findings and redaction_mode == "block":
        fingerprints = ", ".join(sorted({finding.fingerprint for finding in findings}))
        raise ValueError(
            f"record {payload.example_id} contains blocked secret/PII fingerprints: {fingerprints}"
        )
    updates: dict[str, Any] = {
        "pii_secret_scan": ScanResult(
            status="redacted" if findings else "clean",
            scannerVersion=SCANNER_VERSION,
            findingFingerprints=sorted({finding.fingerprint for finding in findings}),
        )
    }
    if findings:
        updates.update(
            input=_redact_value(payload.input),
            target=_redact_value(payload.target),
            policy_context=_redact_value(payload.policy_context),
        )
    return payload.model_copy(update=updates)


def prepare_dataset(config_path: Path, *, workspace: Path) -> tuple[Path, Path]:
    config, raw_config = load_dataset_config(config_path)
    source = resolve_workspace_path(workspace, config.source)
    output = resolve_workspace_path(workspace, config.output)
    manifest_path = resolve_workspace_path(workspace, config.manifest)
    payloads = [
        _scan_and_normalize(
            DatasetPayload.model_validate(
                {key: value for key, value in raw.items() if key != "contentSha256"}
            ),
            redaction_mode=config.redaction_mode,
        )
        for raw in read_jsonl(source)
    ]
    payloads = apply_splits(
        payloads,
        seed=config.split_seed,
        train_ratio=config.split_ratios.train,
        dev_ratio=config.split_ratios.dev,
    )
    duplicates = find_duplicates(payloads, threshold=config.dedupe_threshold)
    if duplicates:
        pair = duplicates[0]
        raise ValueError(
            f"near-duplicate records require review: {pair.left_id}, {pair.right_id} "
            f"({pair.similarity:.3f})"
        )
    records = [DatasetRecord.from_payload(payload) for payload in payloads]
    write_jsonl_atomic(
        output,
        [record.model_dump(mode="json", by_alias=True, exclude_none=False) for record in records],
    )
    manifest = build_manifest(
        manifest_id=manifest_path.stem,
        dataset_path=output,
        records=records,
        config_sha256=hashlib.sha256(raw_config).hexdigest(),
    )
    write_json_atomic(manifest_path, manifest.model_dump(mode="json", by_alias=True))
    return output, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    output, manifest = prepare_dataset(args.config, workspace=args.workspace.resolve())
    print(f"prepared {output}")
    print(f"manifest {manifest}")


if __name__ == "__main__":
    main()
