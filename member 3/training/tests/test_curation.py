from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hermes_training.curation import CurationCandidate, route_candidate
from pydantic import ValidationError


def candidate(**updates: object) -> dict[str, object]:
    values: dict[str, object] = {
        "candidateId": "candidate-1",
        "sourceRunId": "run-1",
        "sourceVersion": "agents-v1",
        "reproduced": True,
        "reproducedAt": datetime.now(UTC),
        "contentRedacted": True,
        "classification": "data",
        "target": {"classification": "bug"},
        "targetAuthor": "human-maintainer",
        "targetCorroborated": True,
        "provenance": "human correction on fixture",
        "reviewer": "reviewer-1",
        "rationale": "corrects a stable classification failure",
        "destination": "dataset",
    }
    values.update(updates)
    return values


def test_reviewed_candidate_is_routed_once() -> None:
    reviewed = CurationCandidate.model_validate(candidate())
    assert route_candidate(reviewed) == "reviewed-dataset"


def test_model_output_cannot_become_label_without_human_target() -> None:
    with pytest.raises(ValidationError, match="human-authored"):
        CurationCandidate.model_validate(
            candidate(targetAuthor=None, targetCorroborated=False)
        )


def test_unredacted_candidate_is_blocked() -> None:
    with pytest.raises(ValidationError, match="redacted"):
        CurationCandidate.model_validate(candidate(contentRedacted=False))

