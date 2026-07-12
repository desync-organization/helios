from helios.agency.registry import AgentDefinition, AgentRegistry
from helios.contracts import CanonicalEvent


def spawn_expert(registry: AgentRegistry, *, name: str, capability: str, run_id: str,
                 base_model_id: str, requested_tools: list[str], allowed_tools: set[str],
                 max_tokens: int = 8000, max_seconds: float = 120) -> tuple[AgentDefinition, CanonicalEvent]:
    if registry.capability_match(capability):
        raise ValueError("a registered expert already satisfies this capability")
    tools = sorted(set(requested_tools) & allowed_tools)
    if set(requested_tools) - allowed_tools:
        raise PermissionError("spawn requested tools outside policy")
    agent = AgentDefinition(name=name, capability=capability, model_id=base_model_id,
                            persona=f"Specialist for {capability}. Follow policy and typed artifacts.",
                            tools=tools, max_tokens=min(max_tokens, 8000), max_seconds=min(max_seconds, 120),
                            origin="spawned", spawned_by=run_id)
    registry.register(agent)
    event = CanonicalEvent(type="agent_spawned", run_id=run_id,
                           payload={"name": name, "origin": "spawned", "capability": capability, "tools": tools})
    return agent, event


def spawn_rust_fixture(registry: AgentRegistry, run_id: str) -> tuple[AgentDefinition, CanonicalEvent]:
    return spawn_expert(registry, name="rust-expert", capability="Rust code cargo",
                        run_id=run_id, base_model_id="qwen2.5-coder-7b",
                        requested_tools=["repo:read", "workspace:write", "command:cargo"],
                        allowed_tools={"repo:read", "workspace:write", "command:cargo"})

