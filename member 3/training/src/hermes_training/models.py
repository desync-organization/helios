"""Versioned, strict contracts for reviewed Hermes dataset records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hermes_training.hashing import sha256_value

Mode = Literal["maintain", "build", "security_audit"]
Split = Literal["train", "dev", "test"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ScanResult(StrictModel):
    status: Literal["clean", "redacted"]
    scanner_version: str = Field(alias="scannerVersion", min_length=1)
    finding_fingerprints: list[str] = Field(default_factory=list, alias="findingFingerprints")


class DatasetPayload(StrictModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    example_id: str = Field(alias="exampleId", min_length=1)
    mode: Mode
    task_type: str = Field(alias="taskType", min_length=1)
    repository_group: str = Field(alias="repositoryGroup", min_length=1)
    thread_id: str = Field(alias="threadId", min_length=1)
    source_url: str | None = Field(default=None, alias="sourceUrl")
    source_commit: str | None = Field(default=None, alias="sourceCommit")
    license: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    collected_at: datetime = Field(alias="collectedAt")
    reviewer: str = Field(min_length=1)
    review_status: Literal["approved"] = Field(alias="reviewStatus")
    input: str | dict[str, Any]
    expected_artifact_type: str = Field(alias="expectedArtifactType", min_length=1)
    target: str | dict[str, Any]
    policy_context: dict[str, Any] = Field(alias="policyContext")
    safety_tags: list[str] = Field(default_factory=list, alias="safetyTags")
    pii_secret_scan: ScanResult = Field(alias="piiSecretScan")
    split: Split | None = None

    def content_hash(self) -> str:
        payload = self.model_dump(mode="json", by_alias=True, exclude_none=False)
        return sha256_value(payload)


class DatasetRecord(DatasetPayload):
    content_sha256: str = Field(alias="contentSha256", pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> DatasetRecord:
        payload = self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"content_sha256"},
            exclude_none=False,
        )
        if self.content_sha256 != sha256_value(payload):
            raise ValueError("contentSha256 does not match the normalized record")
        return self

    @classmethod
    def from_payload(cls, payload: DatasetPayload) -> DatasetRecord:
        data = payload.model_dump(mode="json", by_alias=True, exclude_none=False)
        data["contentSha256"] = sha256_value(data)
        return cls.model_validate(data)


class DatasetManifest(StrictModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    manifest_id: str = Field(alias="manifestId", min_length=1)
    created_at: datetime = Field(alias="createdAt")
    dataset_path: str = Field(alias="datasetPath", min_length=1)
    dataset_sha256: str = Field(alias="datasetSha256", pattern=r"^[a-f0-9]{64}$")
    record_count: int = Field(alias="recordCount", ge=1)
    split_counts: dict[Split, int] = Field(alias="splitCounts")
    mode_counts: dict[Mode, int] = Field(alias="modeCounts")
    record_hashes: list[str] = Field(alias="recordHashes", min_length=1)
    gauntlet_case_hashes: list[str] = Field(default_factory=list, alias="gauntletCaseHashes")
    config_sha256: str = Field(alias="configSha256", pattern=r"^[a-f0-9]{64}$")
    manifest_sha256: str = Field(alias="manifestSha256", pattern=r"^[a-f0-9]{64}$")

