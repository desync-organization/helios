from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


_VERIFIED_ENDPOINT_IDENTITIES: dict[str, str] = {}


class ModelEndpointStatus(BaseModel):
    """A redaction-safe readiness result for an OpenAI-compatible model server."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str
    ready: bool
    expected_model_id: str
    advertised_model_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class LlamaClient:
    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float,
        expected_model_id: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.expected_model_id = expected_model_id or _VERIFIED_ENDPOINT_IDENTITIES.get(
            self.endpoint
        )
        self.transport = transport

    async def probe(self, expected_model_id: str | None = None) -> ModelEndpointStatus:
        """Verify both llama.cpp readiness and the exact advertised model identity."""

        expected = expected_model_id or self.expected_model_id
        if not expected:
            raise ValueError(
                "an expected model identity is required for readiness probing"
            )
        _VERIFIED_ENDPOINT_IDENTITIES.pop(self.endpoint, None)
        advertised: list[str] = []
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                health = await client.get(f"{self.endpoint}/health")
                health.raise_for_status()
                health_payload = health.json()
                if (
                    not isinstance(health_payload, dict)
                    or health_payload.get("status") != "ok"
                ):
                    raise ValueError("model server health response is not ready")

                models = await client.get(f"{self.endpoint}/v1/models")
                models.raise_for_status()
                advertised = _advertised_model_ids(models.json())
                if expected not in advertised:
                    raise ValueError("model server advertised an unexpected identity")
        except (httpx.HTTPError, ValueError) as exc:
            return ModelEndpointStatus(
                endpoint=self.endpoint,
                ready=False,
                expected_model_id=expected,
                advertised_model_ids=advertised,
                error=_safe_probe_error(exc),
            )
        _VERIFIED_ENDPOINT_IDENTITIES[self.endpoint] = expected
        return ModelEndpointStatus(
            endpoint=self.endpoint,
            ready=True,
            expected_model_id=expected,
            advertised_model_ids=advertised,
        )

    async def completion(
        self,
        *,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "artifact", "schema": json_schema},
            },
        }
        if self.expected_model_id:
            request["model"] = self.expected_model_id
        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self.transport
        ) as client:
            response = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                json=request,
            )
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError("model server returned a non-object response")
            if self.expected_model_id and value.get("model") != self.expected_model_id:
                raise ValueError(
                    "model completion identity does not match the requested model"
                )
            return value


def _advertised_model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("model server returned an invalid model catalogue")
    identifiers = [
        item.get("id")
        for item in payload["data"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if not identifiers:
        raise ValueError("model server advertised no model identities")
    return sorted(set(identifiers))


def _safe_probe_error(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http-{exc.response.status_code}"
    if isinstance(exc, httpx.HTTPError):
        return "connection-error"
    return str(exc)
