import pytest
from pydantic import ValidationError

from helios.contracts import ArtifactType, Budget, Plan, PlanNode
from helios.contracts.plan import NodeKind
from helios.planning.fallback_templates import fallback_plan
from helios.planning.validator import PlanPolicy, validate_plan


def test_wire_contract_round_trip_uses_camel_case(maintain_task):
    payload = maintain_task.model_dump(mode="json", by_alias=True)
    assert "schemaVersion" in payload and "taskId" in payload and "policyVersion" in payload
    assert maintain_task == type(maintain_task).model_validate(payload)


def test_cycle_fails(maintain_task):
    with pytest.raises(ValidationError, match="cycle"):
        Plan(task_id=maintain_task.task_id, policy_version="p1", terminal_node_id="a", nodes=[
            PlanNode(node_id="a", expert="intent", output_artifact=ArtifactType.WRITEBACK_INTENT,
                     dependencies=["b"], acceptance_criteria=["valid"], kind=NodeKind.INTENT),
            PlanNode(node_id="b", expert="critic", output_artifact=ArtifactType.CRITIC_VERDICT,
                     dependencies=["a"], acceptance_criteria=["valid"], kind=NodeKind.CRITIC),
        ])


def test_missing_dependency_fails(maintain_task):
    with pytest.raises(ValidationError, match="missing dependencies"):
        Plan(task_id=maintain_task.task_id, policy_version="p1", terminal_node_id="a", nodes=[
            PlanNode(node_id="a", expert="intent", output_artifact=ArtifactType.WRITEBACK_INTENT,
                     dependencies=["missing"], acceptance_criteria=["valid"], kind=NodeKind.INTENT),
        ])


def test_policy_requires_critic_and_bounded_tools(maintain_task):
    plan = fallback_plan(maintain_task)
    policy = PlanPolicy(registered_experts={node.expert for node in plan.nodes},
                        allowed_tools={"repo:read", "workspace:write", "command:test", "scanner:local"})
    assert validate_plan(plan, policy) is plan
    bad = plan.model_copy(deep=True)
    bad.nodes[0].tool_grants = ["github:write"]
    with pytest.raises(ValueError, match="disallowed tools"):
        validate_plan(bad, policy)


def test_excessive_budget_fails(maintain_task):
    plan = fallback_plan(maintain_task)
    plan.nodes[0].budget = Budget(max_tokens=20_000, max_seconds=20)
    policy = PlanPolicy(registered_experts={node.expert for node in plan.nodes}, allowed_tools=set(), max_tokens_per_node=10_000)
    with pytest.raises(ValueError, match="token policy"):
        validate_plan(plan, policy)

