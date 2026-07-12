import json
from typing import Any

from helios.models.client import LlamaClient
from helios.models.manager import ModelManager

from .grammar import plan_json_schema


class LlamaPlanGenerator:
    def __init__(self, manager: ModelManager) -> None:
        self.manager = manager

    async def __call__(self, context: dict[str, Any], repair: bool) -> dict[str, Any]:
        definition = await self.manager.acquire("planner")
        instruction = (
            "Create a typed, per-request DAG. Use only listed experts and tools. Every node needs explicit "
            "acceptance criteria and bounded budgets. Independent branches should overlap. The terminal intent "
            "must depend directly on an independent critic. Security-sensitive work requires the security expert."
        )
        if repair:
            instruction += " This is the single schema-repair attempt: correct structure only; do not relax policy."
        response = await LlamaClient(definition.endpoint, timeout=30).completion(
            messages=[{"role": "system", "content": instruction},
                      {"role": "user", "content": json.dumps(context, sort_keys=True, default=str)}],
            json_schema=plan_json_schema(), max_tokens=3000,
        )
        raw = response["choices"][0]["message"]["content"]
        return json.loads(raw) if isinstance(raw, str) else raw

