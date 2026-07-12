from typing import Any

import httpx


async def proxied_research(proxy_url: str, query: str, policy_ids: list[str]) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(proxy_url, json={"query": query, "policyIds": policy_ids})
        response.raise_for_status()
        return response.json().get("results", [])

