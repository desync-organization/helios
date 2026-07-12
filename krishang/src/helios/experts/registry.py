from .base import ExpertHandler, deterministic_expert


def default_experts() -> dict[str, ExpertHandler]:
    names = {
        "triage", "dedupe", "web-typescript", "backend", "test", "docs", "debug",
        "security", "research", "critic", "product", "architect", "integration", "intent",
    }
    return {name: deterministic_expert for name in names}

