"""Stable repository/thread-grouped dataset splitting."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from hermes_training.models import DatasetPayload, Split


def _bucket(group_key: str, seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{group_key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def assign_split(
    record: DatasetPayload,
    *,
    seed: int,
    train_ratio: float,
    dev_ratio: float,
) -> Split:
    if train_ratio <= 0 or dev_ratio < 0 or train_ratio + dev_ratio >= 1:
        raise ValueError("split ratios must leave positive train and test partitions")
    group_key = f"{record.repository_group}\0{record.thread_id}"
    value = _bucket(group_key, seed)
    if value < train_ratio:
        return "train"
    if value < train_ratio + dev_ratio:
        return "dev"
    return "test"


def apply_splits(
    records: Iterable[DatasetPayload],
    *,
    seed: int,
    train_ratio: float = 0.8,
    dev_ratio: float = 0.1,
) -> list[DatasetPayload]:
    return [
        record.model_copy(
            update={
                "split": assign_split(
                    record,
                    seed=seed,
                    train_ratio=train_ratio,
                    dev_ratio=dev_ratio,
                )
            }
        )
        for record in records
    ]
