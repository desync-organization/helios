from helios.contracts import NormalizedTask, Plan
from helios.planning.fallback_templates import maintain_plan


def plan_for_maintenance(task: NormalizedTask) -> Plan:
    return maintain_plan(task)

