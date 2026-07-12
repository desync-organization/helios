import asyncio
from typing import Any

import httpx

from helios.contracts import Artifact, CanonicalEvent, Span

from .base import ControlPlane, Lease, LeaseLost
from .outbox import IdempotentOutbox


class ConvexHttpControlPlane(ControlPlane):
    def __init__(self, base_url: str, token: str, *, timeout: float = 10,
                 outbox: IdempotentOutbox | None = None) -> None:
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        self.outbox = outbox

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        for attempt in range(3):
            response = await self.client.request(method, path, json=json)
            if response.status_code in (401, 403, 422):
                response.raise_for_status()
            if response.status_code == 409:
                raise LeaseLost("control plane reports a lost lease")
            if response.status_code != 429 and response.status_code < 500:
                response.raise_for_status()
                return response.json() if response.content else None
            if attempt == 2:
                response.raise_for_status()
            await asyncio.sleep(0.25 * (2**attempt))

    async def claim(self, instance_id: str) -> Lease | None:
        if self.outbox:
            try:
                await self.outbox.replay(lambda record: self._request(
                    record["payload"]["method"], record["payload"]["path"], record["payload"]["body"]
                ))
            except (httpx.HTTPError, LeaseLost):
                pass
        value = await self._request("POST", "/runtime/claim", {"instanceId": instance_id})
        return Lease.model_validate(value) if value else None

    async def heartbeat(self, lease_id: str) -> Lease:
        return Lease.model_validate(await self._request("POST", "/runtime/heartbeat", {"leaseId": lease_id}))

    async def lease_valid(self, lease_id: str) -> bool:
        try:
            await self.heartbeat(lease_id)
            return True
        except LeaseLost:
            return False

    async def emit_event(self, event: CanonicalEvent) -> None:
        await self._durable_post("/runtime/span", event.event_id, event.model_dump(mode="json", by_alias=True))

    async def store_span(self, span: Span) -> None:
        await self._durable_post("/runtime/span", span.span_id, span.model_dump(mode="json", by_alias=True))

    async def store_artifact(self, artifact: Artifact) -> None:
        await self._durable_post("/runtime/artifact", artifact.artifact_id, artifact.model_dump(mode="json", by_alias=True))

    async def finish_run(self, run_id: str, result: dict[str, Any]) -> None:
        await self._durable_post("/runtime/run/finish", f"finish:{run_id}", {"runId": run_id, **result})

    async def submit_intent(self, lease_id: str, intent: Artifact) -> None:
        await self._request("POST", "/runtime/writeback", {"leaseId": lease_id, "intent": intent.model_dump(mode="json")})

    async def _durable_post(self, path: str, record_id: str, body: dict[str, Any]) -> None:
        try:
            await self._request("POST", path, body)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (429,) and exc.response.status_code < 500:
                raise
            if not self.outbox:
                raise
            await self.outbox.append(record_id, "control-plane", {"method": "POST", "path": path, "body": body})
        except httpx.RequestError:
            if not self.outbox:
                raise
            await self.outbox.append(record_id, "control-plane", {"method": "POST", "path": path, "body": body})
