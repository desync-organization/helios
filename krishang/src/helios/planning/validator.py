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


def validate_plan(
    plan: Plan,
    policy: PlanPolicy,
    *,
    mode: str | None = None,
    task_id: str | None = None,
    policy_version: str | None = None,
) -> Plan:
    artifact_types = {item.value for item in ArtifactType}
    catalog = {str(item.get("name")): item for item in policy.agent_catalog if item.get("name")}
    nodes = {node.node_id: node for node in plan.nodes}
    terminal = nodes[plan.terminal_node_id]
    if task_id and plan.task_id != task_id:
        raise ValueError("plan task ID does not match the claimed task")
    if policy_version and plan.policy_version != policy_version:
        raise ValueError("plan policy version does not match the claimed task")
    if terminal.kind != NodeKind.INTENT:
        raise ValueError("terminal node must produce an intent")
    critics = [node for node in plan.nodes if node.kind == NodeKind.CRITIC]
    if not critics or not terminal.dependencies or any(nodes[item].kind != NodeKind.CRITIC for item in terminal.dependencies):
        raise ValueError("an independent critic must directly gate the terminal intent")
    ancestors: set[str] = set()
    pending = list(terminal.dependencies)
    while pending:
        node_id = pending.pop()
        if node_id in ancestors:
            continue
        ancestors.add(node_id)
        pending.extend(nodes[node_id].dependencies)
    disconnected = set(nodes) - ancestors - {terminal.node_id}
    if disconnected:
        raise ValueError(f"plan contains work disconnected from the terminal critic: {sorted(disconnected)}")
    for node in plan.nodes:
        definition = catalog.get(node.expert)
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
        if definition:
            if definition.get("status") == "paused":
                raise ValueError(f"expert is paused: {node.expert}")
            if mode and mode not in set(definition.get("modes", [])):
                raise ValueError(f"expert {node.expert} does not support mode {mode}")
            if set(node.tool_grants) - set(definition.get("tools", [])):
                raise ValueError(f"node {node.node_id} exceeds expert tool grants")
            if node.output_artifact not in set(definition.get("produces", [])):
                raise ValueError(f"expert {node.expert} cannot produce {node.output_artifact}")
            if node.budget.max_tokens > int(definition.get("maxTokens", policy.max_tokens_per_node)):
                raise ValueError(f"node {node.node_id} exceeds expert token budget")
            if node.budget.max_seconds > float(definition.get("maxSeconds", policy.max_seconds_per_node)):
                raise ValueError(f"node {node.node_id} exceeds expert time budget")
        if set(node.tool_grants) - policy.allowed_tools:
            raise ValueError(f"node {node.node_id} requests disallowed tools")
        if node.budget.max_tokens > policy.max_tokens_per_node:
            raise ValueError(f"node {node.node_id} exceeds token policy")
        if node.budget.max_seconds > policy.max_seconds_per_node:
            raise ValueError(f"node {node.node_id} exceeds time policy")
        if node.sensitive and "security" not in {n.expert for n in plan.nodes}:
            raise ValueError("sensitive work requires the security expert")
    return plan
