from typing import Any

from pydantic import Field
from .common import WireModel


class RepositoryInventory(WireModel):
    repository: str
    commit_sha: str
    languages: list[str] = Field(default_factory=list)
    manifests: list[str] = Field(default_factory=list)
    lockfiles: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    infrastructure_files: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    coverage_limitations: list[str] = Field(default_factory=list)


class Finding(WireModel):
    fingerprint: str
    kind: str
    rule_id: str
    title: str
    severity: str
    confidence: str
    exploitability: str = "unproven"
    reachability: str = "unknown"
    path: str
    line: int | None = None
    evidence: str = ""
    remediation: str = ""
    advisory_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScannerResult(WireModel):
    scanner: str
    scanner_version: str
    rule_database_version: str = "unknown"
    command_hash: str
    config: dict[str, Any] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    exit_code: int
    output_ref: str
    findings: list[Finding] = Field(default_factory=list)
