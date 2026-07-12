from typing import Literal

from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    name: str
    version: str = "1.0"
    capability: str
    model_id: str
    persona: str
    tools: list[str] = Field(default_factory=list)
    max_tokens: int = 4000
    max_seconds: float = 120
    origin: Literal["kickoff", "spawned"] = "kickoff"
    spawned_by: str | None = None
    adapter_id: str | None = None


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

