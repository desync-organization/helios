"""Human-gated closed-loop curation; no trace can silently become training truth."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CurationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)

    candidate_id: str = Field(alias="candidateId")
    source_run_id: str = Field(alias="sourceRunId")
    source_version: str = Field(alias="sourceVersion")
    reproduced: bool
    reproduced_at: datetime | None = Field(default=None, alias="reproducedAt")
    content_redacted: bool = Field(alias="contentRedacted")
    classification: Literal["product_bug", "policy_bug", "prompt_bug", "data", "eval_only"]
    target: str | dict[str, object] | None
    target_author: str | None = Field(default=None, alias="targetAuthor")
    target_corroborated: bool = Field(alias="targetCorroborated")
    provenance: str
    reviewer: str | None = None
    rationale: str | None = None
    destination: Literal["dataset", "eval", "discard"]

    @model_validator(mode="after")
    def enforce_human_review(self) -> CurationCandidate:
        if not self.reproduced or self.reproduced_at is None:
            raise ValueError("candidate must be reproduced against the frozen input/version")
        if not self.content_redacted:
            raise ValueError("candidate must be redacted before review")
        if self.destination != "discard":
            if self.target is None or not self.target_author or not self.target_corroborated:
                raise ValueError(
                    "dataset/eval candidates require a human-authored corroborated target"
                )
            if not self.reviewer or not self.rationale:
                raise ValueError("dataset/eval candidates require reviewer and rationale")
        return self


def route_candidate(
    candidate: CurationCandidate,
) -> Literal["reviewed-dataset", "audited-eval-commit", "discarded"]:
    if candidate.destination == "dataset":
        return "reviewed-dataset"
    if candidate.destination == "eval":
        return "audited-eval-commit"
    return "discarded"
