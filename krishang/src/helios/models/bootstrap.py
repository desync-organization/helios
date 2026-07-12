from typing import Any


def preflight(settings: Any | None = None) -> dict[str, Any]:
    configured = bool(settings and settings.llama_planner_url and settings.llama_triage_url and settings.llama_coder_url)
    return {
        "ready": configured if settings is not None else True,
        "mode": "configured" if configured else "deterministic",
        "credentialsPresent": False,
    }
