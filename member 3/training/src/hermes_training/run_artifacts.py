"""Atomic training-run metadata, metrics, and checksum handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hermes_training.hashing import sha256_file
from hermes_training.io import write_json_atomic


def write_checksums(root: Path) -> dict[str, str]:
    checksums = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }
    write_json_atomic(root / "checksums.json", checksums)
    return checksums


def verify_checksums(root: Path) -> dict[str, str]:
    path = root / "checksums.json"
    expected: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    for relative, checksum in expected.items():
        candidate = root / relative
        if not candidate.is_file() or sha256_file(candidate) != checksum:
            raise ValueError(f"checksum mismatch: {relative}")
    return expected


def write_run_status(root: Path, *, status: str, details: dict[str, Any]) -> None:
    write_json_atomic(root / "status.json", {"status": status, **details})
