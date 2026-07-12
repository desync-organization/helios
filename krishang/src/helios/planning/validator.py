from dataclasses import dataclass, field

from helios.contracts import ArtifactType, Plan
from helios.contracts.plan import NodeKind


@dataclass(slots=True)
class PlanPolicy:
    registered_experts: set[str]
    allowed_tools: set[str]
    agent_catalog: list[dict] = field(default_factory=list)
    max_tokens_per_node: int = 10_000
    max_seconds_per_node: float = 600
    sensitive_policy_ids: set[str] = field(default_factory=set)


def validate_plan(plan: Plan, policy: PlanPolicy) -> Plan:
    artifact_types = {item.value for item in ArtifactType}
    nodes = {node.node_id: node for node in plan.nodes}
    terminal = nodes[plan.terminal_node_id]
    if terminal.kind != NodeKind.INTENT:
        raise ValueError("terminal node must produce an intent")
    critics = [node for node in plan.nodes if node.kind == NodeKind.CRITIC]
    if not critics or not any(critic.node_id in terminal.dependencies for critic in critics):
        raise ValueError("an independent critic must directly gate the terminal intent")
    for node in plan.nodes:
        if node.output_artifact not in artifact_types:
            raise ValueError(f"unknown artifact type: {node.output_artifact}")
        if node.expert not in policy.registered_experts and node.spawn is None:
            raise ValueError(f"expert is not registered: {node.expert}")
        if node.spawn:
            if node.expert != node.spawn.name:
                raise ValueError(f"spawn name must match node expert for {node.node_id}")
            if set(node.spawn.tools) - policy.allowed_tools:
                raise ValueError(f"spawn for {node.node_id} requests disallowed tools")
            if set(node.spawn.tools) - set(node.tool_grants):
                raise ValueError(f"spawn for {node.node_id} exceeds the node's tool grants")
        if set(node.tool_grants) - policy.allowed_tools:
            raise ValueError(f"node {node.node_id} requests disallowed tools")
        if node.budget.max_tokens > policy.max_tokens_per_node:
            raise ValueError(f"node {node.node_id} exceeds token policy")
        if node.budget.max_seconds > policy.max_seconds_per_node:
            raise ValueError(f"node {node.node_id} exceeds time policy")
        if node.sensitive and "security" not in {n.expert for n in plan.nodes}:
            raise ValueError("sensitive work requires the security expert")
    return plan
