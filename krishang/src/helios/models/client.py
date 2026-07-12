from typing import Any

import httpx


class LlamaClient:
    def __init__(self, endpoint: str, *, timeout: float) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def completion(self, *, messages: list[dict[str, str]], json_schema: dict[str, Any], max_tokens: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0,
                    "response_format": {"type": "json_schema", "json_schema": {"name": "artifact", "schema": json_schema}},
                },
            )
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError("model server returned a non-object response")
            return value
