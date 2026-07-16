from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvalContract(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class EvalTelemetry(EvalContract):
    tokens_in: int = Field(alias="tokensIn", ge=0)
    tokens_out: int = Field(alias="tokensOut", ge=0)
    latency_ms: int = Field(alias="latencyMs", ge=0)
    peak_ram_mb: float = Field(alias="peakRamMb", ge=0)
    peak_vram_mb: float = Field(alias="peakVramMb", ge=0)
    cost_usd: float = Field(alias="costUsd", ge=0)
    cost_cloud_equivalent_usd: float = Field(alias="costCloudEquivalentUsd", ge=0)
    execution_location: Literal["local", "remote"] = Field(alias="executionLocation")
    cold_start: bool = Field(alias="coldStart")


class EvalCheck(EvalContract):
    kind: str
    path: str
    passed: bool
    automatic_failure: bool = Field(alias="automaticFailure")
    reason: str


class EvalCaseScore(EvalContract):
    case_id: str = Field(alias="caseId")
    suite: Literal["maintain", "build", "security_audit"]
    category: str
    passed: bool
    score: float = Field(ge=0, le=1)
    automatic_failure: bool = Field(alias="automaticFailure")
    checks: list[EvalCheck] = Field(min_length=1)
    telemetry: EvalTelemetry


class SecurityMetrics(EvalContract):
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    false_positive_rate: float = Field(alias="falsePositiveRate", ge=0, le=1)
    secret_leak_count: int = Field(alias="secretLeakCount", ge=0)
    unauthorized_action_count: int = Field(alias="unauthorizedActionCount", ge=0)
    unsupported_cve_claim_count: int = Field(alias="unsupportedCveClaimCount", ge=0)


class PromotionEvalReport(EvalContract):
    """The Member 3 SuiteReport contract required to authorize promotion."""

    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    report_id: str = Field(alias="reportId", min_length=1)
    configuration: str = Field(min_length=1)
    seed: int
    case_set_sha256: str = Field(alias="caseSetSha256", pattern=r"^[a-f0-9]{64}$")
    created_at: datetime = Field(alias="createdAt")
    case_count: int = Field(alias="caseCount", ge=1)
    passed_count: int = Field(alias="passedCount", ge=0)
    pass_rate: float = Field(alias="passRate", ge=0, le=1)
    category_pass_rates: dict[str, float] = Field(alias="categoryPassRates")
    automatic_failure_count: int = Field(alias="automaticFailureCount", ge=0)
    gate_passed: bool = Field(alias="gatePassed")
    gate_blockers: list[str] = Field(alias="gateBlockers")
    total_tokens_in: int = Field(alias="totalTokensIn", ge=0)
    total_tokens_out: int = Field(alias="totalTokensOut", ge=0)
    total_cost_usd: float = Field(alias="totalCostUsd", ge=0)
    total_cloud_equivalent_cost_usd: float = Field(
        alias="totalCloudEquivalentCostUsd",
        ge=0,
    )
    latency_p50_ms: float = Field(alias="latencyP50Ms", ge=0)
    latency_p95_ms: float = Field(alias="latencyP95Ms", ge=0)
    security_metrics: SecurityMetrics | None = Field(
        default=None, alias="securityMetrics"
    )
    cases: list[EvalCaseScore]

    @model_validator(mode="after")
    def validate_gate_evidence(self) -> "PromotionEvalReport":
        if not self.gate_passed:
            raise ValueError("evaluation gate did not pass")
        if self.gate_blockers:
            raise ValueError("evaluation report contains gate blockers")
        if self.automatic_failure_count:
            raise ValueError("evaluation report contains automatic failures")
        if self.passed_count > self.case_count:
            raise ValueError("evaluation passedCount exceeds caseCount")
        if len(self.cases) != self.case_count:
            raise ValueError("evaluation case evidence does not match caseCount")
        actual_passed = sum(item.passed for item in self.cases)
        if actual_passed != self.passed_count:
            raise ValueError("evaluation case evidence does not match passedCount")
        actual_automatic_failures = sum(item.automatic_failure for item in self.cases)
        if actual_automatic_failures != self.automatic_failure_count:
            raise ValueError("evaluation cases do not match automaticFailureCount")
        expected_rate = self.passed_count / self.case_count
        if abs(self.pass_rate - expected_rate) > 1e-9:
            raise ValueError("evaluation passRate does not match case counts")
        if self.total_tokens_in != sum(item.telemetry.tokens_in for item in self.cases):
            raise ValueError("evaluation totalTokensIn does not match case telemetry")
        if self.total_tokens_out != sum(
            item.telemetry.tokens_out for item in self.cases
        ):
            raise ValueError("evaluation totalTokensOut does not match case telemetry")
        if (
            abs(
                self.total_cost_usd
                - sum(item.telemetry.cost_usd for item in self.cases)
            )
            > 1e-9
        ):
            raise ValueError("evaluation totalCostUsd does not match case telemetry")
        if (
            abs(
                self.total_cloud_equivalent_cost_usd
                - sum(item.telemetry.cost_cloud_equivalent_usd for item in self.cases)
            )
            > 1e-9
        ):
            raise ValueError(
                "evaluation totalCloudEquivalentCostUsd does not match case telemetry"
            )
        return self


def load_passing_eval_report(path: Path) -> PromotionEvalReport:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("evaluation report is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("evaluation report must be a JSON object")
    return PromotionEvalReport.model_validate(payload)
