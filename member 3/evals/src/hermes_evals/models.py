"""Strict contracts for frozen cases, execution results, and reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from hermes_training.hashing import sha256_value
from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["maintain", "build", "security_audit"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class HardCheck(ContractModel):
    kind: Literal[
        "equals",
        "contains_all",
        "forbids_all",
        "is_true",
        "is_false",
        "has_url",
        "finding_set",
    ]
    path: str
    expected: Any
    automatic_failure: bool = Field(default=False, alias="automaticFailure")


class EvalCase(ContractModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    case_id: str = Field(alias="caseId", pattern=r"^[a-z][a-z0-9-]+$")
    suite: Mode
    category: str
    title: str
    fixture: Literal[True] = True
    source_license: str = Field(alias="sourceLicense")
    input: dict[str, Any]
    checks: list[HardCheck] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    case_sha256: str = Field(alias="caseSha256", pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def verify_hash(self) -> EvalCase:
        payload = self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"case_sha256"},
        )
        if sha256_value(payload) != self.case_sha256:
            raise ValueError("caseSha256 does not match frozen case contents")
        return self


class Telemetry(ContractModel):
    tokens_in: int = Field(alias="tokensIn", ge=0)
    tokens_out: int = Field(alias="tokensOut", ge=0)
    latency_ms: int = Field(alias="latencyMs", ge=0)
    peak_ram_mb: float = Field(alias="peakRamMb", ge=0)
    peak_vram_mb: float = Field(alias="peakVramMb", ge=0)
    cost_usd: float = Field(alias="costUsd", ge=0)
    cost_cloud_equivalent_usd: float = Field(alias="costCloudEquivalentUsd", ge=0)
    execution_location: Literal["local", "remote"] = Field(alias="executionLocation")
    cold_start: bool = Field(alias="coldStart")


class EvalResult(ContractModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    case_id: str = Field(alias="caseId")
    configuration: str
    seed: int
    output: dict[str, Any]
    telemetry: Telemetry


class CheckResult(ContractModel):
    kind: str
    path: str
    passed: bool
    automatic_failure: bool = Field(alias="automaticFailure")
    reason: str


class CaseScore(ContractModel):
    case_id: str = Field(alias="caseId")
    suite: Mode
    category: str
    passed: bool
    score: float = Field(ge=0, le=1)
    automatic_failure: bool = Field(alias="automaticFailure")
    checks: list[CheckResult]
    telemetry: Telemetry


class SecurityMetrics(ContractModel):
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    false_positive_rate: float = Field(alias="falsePositiveRate", ge=0, le=1)
    secret_leak_count: int = Field(alias="secretLeakCount", ge=0)
    unauthorized_action_count: int = Field(alias="unauthorizedActionCount", ge=0)
    unsupported_cve_claim_count: int = Field(alias="unsupportedCveClaimCount", ge=0)


class SuiteReport(ContractModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    report_id: str = Field(alias="reportId")
    configuration: str
    seed: int
    case_set_sha256: str = Field(alias="caseSetSha256")
    created_at: datetime = Field(alias="createdAt")
    case_count: int = Field(alias="caseCount")
    passed_count: int = Field(alias="passedCount")
    pass_rate: float = Field(alias="passRate", ge=0, le=1)
    category_pass_rates: dict[str, float] = Field(alias="categoryPassRates")
    automatic_failure_count: int = Field(alias="automaticFailureCount")
    gate_passed: bool = Field(alias="gatePassed")
    gate_blockers: list[str] = Field(alias="gateBlockers")
    total_tokens_in: int = Field(alias="totalTokensIn")
    total_tokens_out: int = Field(alias="totalTokensOut")
    total_cost_usd: float = Field(alias="totalCostUsd")
    total_cloud_equivalent_cost_usd: float = Field(alias="totalCloudEquivalentCostUsd")
    latency_p50_ms: float = Field(alias="latencyP50Ms")
    latency_p95_ms: float = Field(alias="latencyP95Ms")
    security_metrics: SecurityMetrics | None = Field(default=None, alias="securityMetrics")
    cases: list[CaseScore]
