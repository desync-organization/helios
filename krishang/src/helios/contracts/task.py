from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from helios.clock import now_utc
from helios.ids import new_id
from .common import WireModel


class RuntimeMode(StrEnum):
    MAINTAIN = "maintain"
    BUILD = "build"
    SECURITY_AUDIT = "security_audit"


class TaskType(StrEnum):
    INTAKE = "intake"
    CLASSIFY = "classify"
    LABEL = "label"
    DEDUPE = "dedupe"
    CLARIFY = "clarify"
    RESPOND = "respond"
    REPRO = "repro"
    FIX = "fix"
    REVIEW = "review"
    DOCS = "docs"
    RELEASE = "release"
    ESCALATE = "escalate"
    FEATURE = "feature"
    NEW_PROJECT = "new_project"
    AUDIT = "audit"
    REMEDIATE = "remediate"


class ConsentScope(WireModel):
    repository_allowlisted: bool = False
    security_audit_opt_in: bool = False
    remediation_permitted: bool = False
    network_permitted: bool = False
    deployment_permitted: bool = False
    allowed_scanners: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=lambda: ["."])
    excluded_paths: list[str] = Field(default_factory=lambda: [".git", "node_modules"])
    max_runtime_s: int = 600


class NormalizedTask(WireModel):

    schema_version: str = "1.0"
    task_id: str = Field(default_factory=lambda: new_id("task"))
    mode: RuntimeMode
    task_type: TaskType
    repository: str
    base_sha: str
    policy_version: str
    title: str
    body: str = ""
    source: str = "ui"
    visibility: str = "private"
    consent: ConsentScope
    memory_pack: dict[str, Any] = Field(default_factory=dict)
    policy_pack: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)

    def assert_authorized(self) -> None:
        if not self.consent.repository_allowlisted:
            raise ValueError("repository is not allowlisted")
        if self.mode == RuntimeMode.SECURITY_AUDIT and not self.consent.security_audit_opt_in:
            raise ValueError("security audit requires explicit opt-in")
        if self.mode == RuntimeMode.SECURITY_AUDIT and (
            self.metadata.get("externalTarget") or self.metadata.get("exploitRequested")
        ):
            raise ValueError("external target and exploit requests are forbidden")
        if self.task_type == TaskType.REMEDIATE and not self.consent.remediation_permitted:
            raise ValueError("security remediation requires separate authorization")
        if self.mode == RuntimeMode.BUILD and self.metadata.get("productionChange") and not self.consent.deployment_permitted:
            raise ValueError("production changes require explicit consent")
