"""Compare v1-v4 reports only when cases and seeds are identical."""

from __future__ import annotations

from dataclasses import dataclass

from hermes_evals.models import SuiteReport


@dataclass(frozen=True, slots=True)
class RegressionDelta:
    baseline: str
    candidate: str
    pass_rate_delta: float
    latency_p95_delta_ms: float
    cost_delta_usd: float
    cloud_equivalent_cost_delta_usd: float


def compare_reports(baseline: SuiteReport, candidate: SuiteReport) -> RegressionDelta:
    if baseline.case_set_sha256 != candidate.case_set_sha256:
        raise ValueError("regression reports must use the identical frozen case set")
    if baseline.seed != candidate.seed:
        raise ValueError("regression reports must use the identical evaluation seed")
    return RegressionDelta(
        baseline=baseline.configuration,
        candidate=candidate.configuration,
        pass_rate_delta=candidate.pass_rate - baseline.pass_rate,
        latency_p95_delta_ms=candidate.latency_p95_ms - baseline.latency_p95_ms,
        cost_delta_usd=candidate.total_cost_usd - baseline.total_cost_usd,
        cloud_equivalent_cost_delta_usd=(
            candidate.total_cloud_equivalent_cost_usd
            - baseline.total_cloud_equivalent_cost_usd
        ),
    )

