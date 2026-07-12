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


def model_expert(manager: ModelManager, expert_name: str, *, role_override: str | None = None,
                 adapter: dict[str, Any] | None = None) -> ExpertHandler:
    async def run(context: ExpertContext) -> dict[str, Any]:
        # Intent and integration are deterministic hard gates, never model-authored effects.
        if expert_name in {"intent", "integration"}:
            return await deterministic_expert(context)
        role = role_override or ROLE_MODELS.get(expert_name, "triage")
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
        elif expert_name == "html-slm":
            system += " Return complete semantic HTML files only. Never include script, style, inline handlers, or markdown."
        elif expert_name == "css-slm":
            system += " Return complete CSS files only. Never include HTML, JavaScript, remote imports, or markdown."
        elif expert_name == "javascript-slm":
            system += " Return complete browser JavaScript files only. Never use eval, Function, hidden network calls, HTML, CSS, or markdown."
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
        content["_model"] = {
            "baseModel": definition.model_id,
            "baseQuantization": definition.quantization,
            "adapterId": adapter.get("id") if adapter else None,
            "adapterVersion": adapter.get("version") if adapter else None,
            "adapterScale": adapter.get("scale", 0) if adapter else 0,
        }
        # Hard evidence gates override critic confidence.
        if expert_name == "critic":
            if any(item.content.get("success") is False or item.content.get("safe") is False for item in context.upstream):
                content.update({"verdict": "blocked", "notes": ["deterministic upstream gate failed"], "independent": True})
            reviewed = context.upstream[0] if context.upstream else None
            content.update({
                "independent": True,
                "reviewedArtifactId": reviewed.artifact_id if reviewed else "",
                "reviewedContentHash": reviewed.content_hash if reviewed else "",
                "producerAgent": reviewed.producer if reviewed else "unknown",
                "criticAgent": "critic",
            })
        return content
    return run


def model_backed_experts(manager: ModelManager) -> dict[str, ExpertHandler]:
    names = {
        "triage", "dedupe", "web-typescript", "backend", "test", "docs", "debug",
        "security", "research", "critic", "product", "architect", "integration", "intent",
    }
    return {name: model_expert(manager, name) for name in names}
