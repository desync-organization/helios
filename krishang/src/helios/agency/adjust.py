from helios.agency.registry import AgentDefinition


def adjust_persona(agent: AgentDefinition, constraint: str, repeated_failure_count: int) -> AgentDefinition:
    if repeated_failure_count < 2:
        raise ValueError("role adjustment requires repeated normalized critic failures")
    blocked_terms = {"tool", "policy", "guardrail", "adapter", "model", "secret"}
    if blocked_terms & set(constraint.lower().split()):
        raise PermissionError("persona adjustment cannot change protected runtime configuration")
    major, _, minor = agent.version.partition(".")
    return agent.model_copy(update={"version": f"{major}.{int(minor or 0) + 1}",
                                    "persona": f"{agent.persona}\nConstraint: {constraint}"})

