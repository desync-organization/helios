from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest
from hermes_evals.compare import compare_reports
from hermes_evals.models import EvalCase, EvalResult, SuiteReport
from hermes_evals.runner import evaluate
from hermes_training.hashing import sha256_value
from hermes_training.io import read_jsonl


def eval_case(*, automatic: bool = False) -> EvalCase:
    value = {
        "schemaVersion": "1.0",
        "caseId": "maintain-triage-01",
        "suite": "maintain",
        "category": "triage",
        "title": "Classify fixture",
        "fixture": True,
        "sourceLicense": "CC0-1.0",
        "input": {"title": "Crash"},
        "checks": [
            {
                "kind": "equals",
                "path": "classification",
                "expected": "bug",
                "automaticFailure": automatic,
            }
        ],
        "tags": [],
    }
    value["caseSha256"] = sha256_value(value)
    return EvalCase.model_validate(value)


def result(output: dict[str, object]) -> EvalResult:
    return EvalResult.model_validate(
        {
            "caseId": "maintain-triage-01",
            "configuration": "agents-v1",
            "seed": 3407,
            "output": output,
            "telemetry": {
                "tokensIn": 10,
                "tokensOut": 5,
                "latencyMs": 100,
                "peakRamMb": 100,
                "peakVramMb": 0,
                "costUsd": 0,
                "costCloudEquivalentUsd": 0.001,
                "executionLocation": "local",
                "coldStart": False,
            },
        }
    )


def test_deterministic_case_passes() -> None:
    report = evaluate([eval_case()], [result({"classification": "bug"})])
    assert report.gate_passed is True
    assert report.total_cost_usd == 0
    assert report.total_cloud_equivalent_cost_usd == 0.001


def test_secret_leak_is_automatic_failure() -> None:
    report = evaluate(
        [eval_case()],
        [result({"classification": "bug", "text": "ghp_abcdefghijklmnopqrstuvwxyz123456"})],
    )
    assert report.gate_passed is False
    assert report.automatic_failure_count == 1


def report(case_set: str, seed: int) -> SuiteReport:
    return SuiteReport.model_validate(
        {
            "reportId": "report",
            "configuration": "agents-v1",
            "seed": seed,
            "caseSetSha256": case_set,
            "createdAt": datetime.now(UTC),
            "caseCount": 1,
            "passedCount": 1,
            "passRate": 1,
            "categoryPassRates": {"triage": 1},
            "automaticFailureCount": 0,
            "gatePassed": True,
            "gateBlockers": [],
            "totalTokensIn": 1,
            "totalTokensOut": 1,
            "totalCostUsd": 0,
            "totalCloudEquivalentCostUsd": 0.01,
            "latencyP50Ms": 10,
            "latencyP95Ms": 10,
            "cases": [],
        }
    )


def test_comparison_rejects_different_case_sets_or_seeds() -> None:
    with pytest.raises(ValueError, match="case set"):
        compare_reports(report("a", 1), report("b", 1))
    with pytest.raises(ValueError, match="seed"):
        compare_reports(report("a", 1), report("a", 2))


def test_frozen_case_bank_has_required_mode_counts() -> None:
    case_path = Path(__file__).parents[1] / "gauntlet" / "cases-v1.jsonl"
    cases = [EvalCase.model_validate(item) for item in read_jsonl(case_path)]
    assert Counter(case.suite for case in cases) == {
        "maintain": 40,
        "build": 15,
        "security_audit": 20,
    }
