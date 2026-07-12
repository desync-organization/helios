from helios.contracts import NormalizedTask, Plan
from helios.planning.fallback_templates import build_plan


def plan_for_build(task: NormalizedTask) -> Plan:
    return build_plan(task)

