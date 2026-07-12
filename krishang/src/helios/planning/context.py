from typing import Any

from helios.contracts import NormalizedTask


def bounded_context(task: NormalizedTask, experts: list[str], max_chars: int = 16_000) -> dict[str, Any]:
    context = {
        "task": task.model_dump(mode="json", exclude={"body"}),
        "body": task.body[:6000],
        "memory": task.memory_pack,
        "policy": task.policy_pack,
        "repositorySummary": task.metadata.get("repositorySummary", {}),
        "experts": experts,
    }
    text = str(context)
    if len(text) > max_chars:
        context["memory"] = {"truncated": True}
        context["body"] = task.body[:2000]
    return context

