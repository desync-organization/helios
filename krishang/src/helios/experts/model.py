import json
from typing import Any

from helios.models.client import LlamaClient
from helios.models.manager import ModelManager
from helios.security.redaction import redact

from .base import ExpertContext, ExpertHandler, deterministic_expert


ROLE_MODELS = {
    "triage": "triage", "dedupe": "triage", "docs": "triage", "research": "triage",
    "product": "planner", "architect": "planner", "critic": "critic",
    "web-typescript": "coder", "backend": "coder", "test": "coder", "debug": "coder",
    "security": "triage",
}


def model_expert(manager: ModelManager, expert_name: str) -> ExpertHandler:
    async def run(context: ExpertContext) -> dict[str, Any]:
        # Intent and integration are deterministic hard gates, never model-authored effects.
        if expert_name in {"intent", "integration"}:
            return await deterministic_expert(context)
        role = ROLE_MODELS.get(expert_name, "triage")
        definition = await manager.acquire(role, context.run_id)
        client = LlamaClient(definition.endpoint, timeout=context.node.budget.max_seconds)
        payload = {
            "task": context.task.model_dump(mode="json", by_alias=True),
            "expectedArtifact": context.node.output_artifact,
            "acceptanceCriteria": context.node.acceptance_criteria,
            "policyIds": context.node.policy_ids,
            "upstreamArtifacts": [item.model_dump(mode="json", by_alias=True) for item in context.upstream],
            "revisionNotes": context.revision_notes,
        }
        system = (
            f"You are the Helios {expert_name} expert. Return one JSON object for the requested typed artifact. "
            "Never claim a command, test, scan, advisory, package version, or repository fact not present in evidence. "
            "Never request credentials or external effects."
        )
        if expert_name == "critic":
            system += " You are independent from the producing expert. Verdict must be pass, revise, or blocked."
        response = await client.completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": json.dumps(payload, sort_keys=True, default=str)}],
            json_schema={"type": "object", "additionalProperties": True},
            max_tokens=context.node.budget.max_tokens,
        )
        raw = response["choices"][0]["message"]["content"]
        content = redact(json.loads(raw) if isinstance(raw, str) else raw)
        usage = response.get("usage", {})
        content["_usage"] = {"tokens": int(usage.get("completion_tokens", 0)),
                             "costUsd": float(response.get("cost_usd", 0))}
        # Hard evidence gates override critic confidence.
        if expert_name == "critic":
            if any(item.content.get("success") is False or item.content.get("safe") is False for item in context.upstream):
                content.update({"verdict": "blocked", "notes": ["deterministic upstream gate failed"], "independent": True})
            content["independent"] = True
        return content
    return run


def model_backed_experts(manager: ModelManager) -> dict[str, ExpertHandler]:
    names = {
        "triage", "dedupe", "web-typescript", "backend", "test", "docs", "debug",
        "security", "research", "critic", "product", "architect", "integration", "intent",
    }
    return {name: model_expert(manager, name) for name in names}
