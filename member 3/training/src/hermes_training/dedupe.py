"""Deterministic exact and near-duplicate detection across dataset splits."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher

from hermes_training.hashing import sha256_value
from hermes_training.models import DatasetPayload


def normalized_content(record: DatasetPayload) -> str:
    content = json.dumps(
        {"input": record.input, "target": record.target},
        ensure_ascii=False,
        sort_keys=True,
    ).casefold()
    return re.sub(r"\s+", " ", content).strip()


def normalized_hash(record: DatasetPayload) -> str:
    return sha256_value(normalized_content(record))


@dataclass(frozen=True, slots=True)
class DuplicatePair:
    left_id: str
    right_id: str
    similarity: float
    crosses_split: bool


def find_duplicates(
    records: Iterable[DatasetPayload],
    *,
    threshold: float = 0.94,
) -> list[DuplicatePair]:
    items = list(records)
    duplicates: list[DuplicatePair] = []
    normalized = [normalized_content(item) for item in items]
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            similarity = SequenceMatcher(
                None,
                normalized[left_index],
                normalized[right_index],
                autojunk=False,
            ).ratio()
            if similarity >= threshold:
                duplicates.append(
                    DuplicatePair(
                        left_id=left.example_id,
                        right_id=right.example_id,
                        similarity=similarity,
                        crosses_split=left.split != right.split,
                    )
                )
    return duplicates
