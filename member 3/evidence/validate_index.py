"""Validate evidence lineage and prevent fixtures from being counted as live completion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    evidence_id: str = Field(alias="evidenceId")
    title: str
    data_class: Literal["live", "fixture", "rehearsal", "fallback"] = Field(alias="dataClass")
    captured_at: datetime = Field(alias="capturedAt")
    commit_sha: str = Field(alias="commitSha", pattern=r"^[a-f0-9]{7,40}$")
    task_id: str | None = Field(default=None, alias="taskId")
    run_id: str | None = Field(default=None, alias="runId")
    result_urls: list[str] = Field(default_factory=list, alias="resultUrls")
    artifact_paths: list[str] = Field(default_factory=list, alias="artifactPaths")
    versions: dict[str, str]
    demonstrates: str
    counts_as_completion: bool = Field(alias="countsAsCompletion")

    @model_validator(mode="after")
    def enforce_truthful_evidence(self) -> EvidenceItem:
        if self.counts_as_completion:
            if self.data_class != "live":
                raise ValueError("only live evidence may count as completion")
            if not self.task_id or not self.run_id or not self.result_urls:
                raise ValueError("live completion requires task/run IDs and a real result URL")
            if not all(url.startswith("https://") for url in self.result_urls):
                raise ValueError("result URLs must be HTTPS")
        return self


class EvidenceIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    items: list[EvidenceItem]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    args = parser.parse_args()
    value = json.loads(args.index.read_text(encoding="utf-8"))
    index = EvidenceIndex.model_validate(value)
    print(f"validated {len(index.items)} evidence items")


if __name__ == "__main__":
    main()
