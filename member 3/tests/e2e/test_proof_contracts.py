from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evidence.validate_index import EvidenceIndex, EvidenceItem


def test_example_evidence_is_explicitly_non_live() -> None:
    root = Path(__file__).parents[2]
    value = json.loads((root / "evidence" / "index.example.json").read_text(encoding="utf-8"))
    index = EvidenceIndex.model_validate(value)
    assert index.items[0].counts_as_completion is False
    assert index.items[0].data_class == "fixture"


def test_fixture_cannot_count_as_completion() -> None:
    with pytest.raises(ValidationError, match="only live evidence"):
        EvidenceItem.model_validate(
            {
                "evidenceId": "bad",
                "title": "bad fixture claim",
                "dataClass": "fixture",
                "capturedAt": "2026-07-12T00:00:00Z",
                "commitSha": "1234567",
                "taskId": "task",
                "runId": "run",
                "resultUrls": ["https://github.com/example/repo/issues/1"],
                "artifactPaths": [],
                "versions": {},
                "demonstrates": "invalid",
                "countsAsCompletion": True,
            }
        )
