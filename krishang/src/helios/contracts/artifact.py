import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from helios.clock import now_utc
from helios.ids import new_id
from .common import WireModel


class ArtifactType(StrEnum):
    PLAN = "plan"
    CLASSIFICATION = "classification"
    DUP_REPORT = "dup_report"
    RESEARCH = "research"
    REPRO_REPORT = "repro_report"
    PATCH = "patch"
    TEST_RESULT = "test_result"
    SECURITY_REPORT = "security_report"
    REVIEW_NOTES = "review_notes"
    DRAFT_REPLY = "draft_reply"
    CRITIC_VERDICT = "critic_verdict"
    BLOCKED = "blocked"
    ESCALATION = "escalation"
    RELEASE_DRAFT = "release_draft"
    REQUIREMENTS_SPEC = "requirements_spec"
    ARCHITECTURE_DECISION = "architecture_decision"
    IMPLEMENTATION_PLAN = "implementation_plan"
    BUILD_MANIFEST = "build_manifest"
    PACKAGE_RESULT = "package_result"
    DEPLOYMENT_DRAFT = "deployment_draft"
    REPOSITORY_INVENTORY = "repository_inventory"
    DEPENDENCY_INVENTORY = "dependency_inventory"
    SBOM = "sbom"
    SECRET_FINDING = "secret_finding"
    VULNERABILITY_FINDING = "vulnerability_finding"
    THREAT_MODEL = "threat_model"
    REMEDIATION_PLAN = "remediation_plan"
    SARIF_REPORT = "sarif_report"
    WRITEBACK_INTENT = "writeback_intent"


class Artifact(WireModel):
    schema_version: str = "1.0"
    artifact_id: str = Field(default_factory=lambda: new_id("artifact"))
    task_id: str
    run_id: str
    artifact_type: ArtifactType
    producer: str
    producer_version: str = "1.0"
    upstream_artifact_ids: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    content: dict[str, Any]
    content_hash: str
    created_at: datetime = Field(default_factory=now_utc)

    @classmethod
    def create(cls, *, content: dict[str, Any], **values: Any) -> "Artifact":
        encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str).encode()
        return cls(content=content, content_hash=hashlib.sha256(encoded).hexdigest(), **values)
