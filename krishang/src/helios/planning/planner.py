from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import ValidationError

from helios.contracts import CanonicalEvent, NormalizedTask, Plan

from .context import bounded_context
from .fallback_templates import fallback_plan
from .validator import PlanPolicy, validate_plan


PlanGenerator = Callable[[dict[str, Any], bool], Awaitable[dict[str, Any]]]


class Planner:
    def __init__(self, policy: PlanPolicy, generator: PlanGenerator | None = None) -> None:
        self.policy = policy
        self.generator = generator

    async def create_plan(self, task: NormalizedTask) -> tuple[Plan, list[CanonicalEvent]]:
        task.assert_authorized()
        events: list[CanonicalEvent] = []
        if self.generator:
            context = bounded_context(task, sorted(self.policy.registered_experts))
            for repair in (False, True):
                try:
                    generated = await self.generator(context, repair)
                    return validate_plan(Plan.model_validate(generated), self.policy), events
                except (ValidationError, ValueError) as exc:
                    events.append(CanonicalEvent(type="planner_schema_rejected", task_id=task.task_id,
                                                 payload={"repairAttempt": repair, "error": str(exc)[:500]}))
        plan = validate_plan(fallback_plan(task), self.policy)
        events.append(CanonicalEvent(type="planner_fallback", task_id=task.task_id,
                                     payload={"planId": plan.plan_id, "mode": task.mode.value}))
        return plan, events

