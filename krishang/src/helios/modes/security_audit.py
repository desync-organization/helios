from helios.contracts import NormalizedTask, Plan
from helios.planning.fallback_templates import security_plan


def plan_for_security_audit(task: NormalizedTask) -> Plan:
    task.assert_authorized()
    return security_plan(task)

