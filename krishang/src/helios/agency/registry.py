from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = "1.0"
    capability: str
    description: str = ""
    model_id: str
    model_role: str = "triage"
    persona: str
    handler_key: str | None = None
    tools: list[str] = Field(default_factory=list)
    modes: list[str] = Field(default_factory=lambda: ["maintain", "build", "security_audit"])
    produces: list[str] = Field(default_factory=list)
    max_tokens: int = Field(4000, ge=1, le=50_000)
    max_seconds: float = Field(120, gt=0, le=1200)
    origin: Literal["kickoff", "spawned"] = "kickoff"
    spawned_by: str | None = None
    adapter_id: str | None = None
    adapter_version: str | None = None
    adapter_manifest: str | None = None
    status: Literal["active", "paused", "template"] = "active"
    independent: bool = False

    @model_validator(mode="after")
    def validate_definition(self) -> "AgentDefinition":
        allowed_modes = {"maintain", "build", "security_audit"}
        if not self.name or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in self.name):
            raise ValueError("agent name must be a stable lowercase identifier")
        if set(self.modes) - allowed_modes:
            raise ValueError("agent contains an unknown runtime mode")
        if len(self.tools) != len(set(self.tools)):
            raise ValueError("agent tools must be unique")
        if self.independent and self.name != "critic":
            raise ValueError("only the critic may declare independent terminal review")
        return self


class AgentRegistry:
    def __init__(self, agents: list[AgentDefinition] | None = None) -> None:
        self._agents = {agent.name: agent for agent in agents or []}

    def register(self, agent: AgentDefinition) -> None:
        if agent.name in self._agents:
            raise ValueError(f"agent already exists: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> AgentDefinition:
        return self._agents[name]

    def list(self) -> list[AgentDefinition]:
        return sorted(self._agents.values(), key=lambda item: item.name)

    def capability_match(self, capability: str) -> AgentDefinition | None:
        words = set(capability.lower().split())
        matches = [(len(words & set(agent.capability.lower().split())), agent) for agent in self._agents.values()]
        score, agent = max(matches, default=(0, None), key=lambda item: item[0])
        return agent if score > 0 else None
