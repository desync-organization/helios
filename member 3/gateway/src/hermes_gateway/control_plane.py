"""Injectable canonical control-plane client; the gateway stores no task truth."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator
from typing import Protocol

import httpx

from hermes_gateway.models import CanonicalEvent, TaskDraft, TaskReceipt, WrapperStatus


class ControlPlane(Protocol):
    async def create_task(self, draft: TaskDraft, idempotency_key: str) -> TaskReceipt: ...

    async def replay_after(self, event_id: str | None) -> list[CanonicalEvent]: ...

    def events(self) -> AsyncIterator[CanonicalEvent]: ...

    async def statuses(self) -> list[WrapperStatus]: ...


class UnavailableControlPlane:
    async def create_task(self, draft: TaskDraft, idempotency_key: str) -> TaskReceipt:
        del draft, idempotency_key
        raise RuntimeError("canonical control plane is not configured")

    async def replay_after(self, event_id: str | None) -> list[CanonicalEvent]:
        del event_id
        return []

    async def events(self) -> AsyncIterator[CanonicalEvent]:
        while True:
            await asyncio.sleep(60)
            if False:
                yield CanonicalEvent.model_construct()

    async def statuses(self) -> list[WrapperStatus]:
        return []


class HttpControlPlane:
    """Member 2 adapter using proposed `/gateway/*` contract endpoints."""

    def __init__(self, base_url: str, token: str | None, poll_seconds: float) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=15)
        self._poll_seconds = poll_seconds
        self._cursor: str | None = None

    async def create_task(self, draft: TaskDraft, idempotency_key: str) -> TaskReceipt:
        response = await self._client.post(
            "/gateway/task-drafts",
            json=draft.model_dump(mode="json", by_alias=True),
            headers={"Idempotency-Key": idempotency_key},
        )
        response.raise_for_status()
        return TaskReceipt.model_validate(response.json())

    async def replay_after(self, event_id: str | None) -> list[CanonicalEvent]:
        response = await self._client.get("/gateway/events", params={"after": event_id or ""})
        response.raise_for_status()
        values = response.json()
        return [CanonicalEvent.model_validate(value) for value in values]

    async def events(self) -> AsyncIterator[CanonicalEvent]:
        backoff = self._poll_seconds
        while True:
            try:
                events = await self.replay_after(self._cursor)
                for event in events:
                    self._cursor = event.event_id
                    yield event
                backoff = self._poll_seconds
            except (httpx.HTTPError, ValueError):
                jitter = secrets.randbelow(250) / 1000
                backoff = min(backoff * 2 + jitter, 30)
            await asyncio.sleep(backoff)

    async def statuses(self) -> list[WrapperStatus]:
        response = await self._client.get("/gateway/status")
        response.raise_for_status()
        return [WrapperStatus.model_validate(value) for value in response.json()]


class FakeControlPlane:
    """Deterministic test adapter; every record is explicitly fixture-labelled."""

    def __init__(self) -> None:
        self.created: list[tuple[TaskDraft, str]] = []
        self._events: list[CanonicalEvent] = []
        self._queue: asyncio.Queue[CanonicalEvent] = asyncio.Queue()

    async def create_task(self, draft: TaskDraft, idempotency_key: str) -> TaskReceipt:
        self.created.append((draft, idempotency_key))
        return TaskReceipt(taskId=f"fixture-task-{len(self.created)}")

    async def replay_after(self, event_id: str | None) -> list[CanonicalEvent]:
        if event_id is None:
            return list(self._events)
        ids = [event.event_id for event in self._events]
        return self._events[ids.index(event_id) + 1 :] if event_id in ids else list(self._events)

    async def events(self) -> AsyncIterator[CanonicalEvent]:
        while True:
            yield await self._queue.get()

    async def statuses(self) -> list[WrapperStatus]:
        return []

    async def emit(self, event: CanonicalEvent) -> None:
        self._events.append(event)
        await self._queue.put(event)
