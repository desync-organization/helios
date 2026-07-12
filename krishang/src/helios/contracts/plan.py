from enum import StrEnum

from pydantic import Field, model_validator

from helios.ids import new_id
from .common import WireModel


class NodeKind(StrEnum):
    EXPERT = "expert"
    CRITIC = "critic"
    INTEGRATION = "integration"
    INTENT = "intent"


class Budget(WireModel):
    max_tokens: int = Field(1000, ge=1, le=50_000)
    max_seconds: float = Field(30, gt=0, le=1200)
    max_cost_usd: float = Field(0, ge=0, le=1)


class SpawnRequest(WireModel):
    name: str
    capability: str
    base_model_id: str
    tools: list[str] = Field(default_factory=list)


class PlanNode(WireModel):
    node_id: str
    expert: str
    output_artifact: str
    dependencies: list[str] = Field(default_factory=list)
    input_artifacts: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(min_length=1)
    tool_grants: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    kind: NodeKind = NodeKind.EXPERT
    sensitive: bool = False
    spawn: SpawnRequest | None = None


class Plan(WireModel):
    schema_version: str = "1.0"
    plan_id: str = Field(default_factory=lambda: new_id("plan"))
    task_id: str
    policy_version: str
    nodes: list[PlanNode]
    terminal_node_id: str
    fallback: bool = False

    @model_validator(mode="after")
    def validate_graph(self) -> "Plan":
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("plan node IDs must be unique")
        known = set(ids)
        if self.terminal_node_id not in known:
            raise ValueError("terminal node is missing")
        for node in self.nodes:
            missing = set(node.dependencies) - known
            if missing:
                raise ValueError(f"node {node.node_id} has missing dependencies: {sorted(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()
        deps = {node.node_id: node.dependencies for node in self.nodes}

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("plan contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in deps[node_id]:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in ids:
            visit(node_id)
        return self
