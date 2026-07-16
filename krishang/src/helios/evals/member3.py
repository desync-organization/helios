from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[dict[str, Any]] = Field(min_length=1)
    results: list[dict[str, Any]] = Field(min_length=1)


def _local_member3_sources() -> tuple[Path, ...]:
    repository_root = Path(__file__).resolve().parents[4]
    member_root = repository_root / "member 3"
    return member_root / "training" / "src", member_root / "evals" / "src"


@lru_cache(maxsize=1)
def load_member3_evaluator() -> ModuleType:
    """Load Member 3's real `hermes_evals` package, installed or in this checkout."""

    evaluator_installed = importlib.util.find_spec("hermes_evals") is not None
    training_installed = importlib.util.find_spec("hermes_training") is not None
    if not evaluator_installed or not training_installed:
        training_source, eval_source = _local_member3_sources()
        required_sources = [
            source
            for source, installed in (
                (training_source, training_installed),
                (eval_source, evaluator_installed),
            )
            if not installed
        ]
        if not all(path.is_dir() for path in required_sources):
            raise ImportError("Member 3 evaluator sources are unavailable")
        for source in reversed(required_sources):
            source_value = str(source)
            if source_value not in sys.path:
                sys.path.insert(0, source_value)
        importlib.invalidate_caches()

    evaluator = importlib.import_module("hermes_evals")
    required = ("EvalCase", "EvalResult", "SuiteReport", "evaluate")
    missing = [name for name in required if not hasattr(evaluator, name)]
    if missing:
        raise ImportError(
            "Member 3 evaluator has an incompatible interface: " + ", ".join(missing)
        )
    return evaluator


async def run_member3_evaluation(
    payload: dict[str, Any],
    *,
    evaluator: ModuleType | None = None,
) -> dict[str, Any]:
    request = EvaluationRequest.model_validate(payload)
    package = evaluator or load_member3_evaluator()
    cases = [package.EvalCase.model_validate(item) for item in request.cases]
    results = [package.EvalResult.model_validate(item) for item in request.results]

    if inspect.iscoroutinefunction(package.evaluate):
        report = await package.evaluate(cases, results)
    else:
        report = await asyncio.to_thread(package.evaluate, cases, results)
    validated = package.SuiteReport.model_validate(report)
    return validated.model_dump(mode="json", by_alias=True)


def run_member3_cli() -> None:
    load_member3_evaluator()
    runner = importlib.import_module("hermes_evals.runner")
    main = getattr(runner, "main", None)
    if not callable(main):
        raise ImportError("Member 3 evaluator CLI is unavailable")
    main()
