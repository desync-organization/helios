"""FastAPI WebSocket application at the frozen client's localhost:9100 boundary."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any, Literal, cast

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from hermes_gateway.config import GatewayConfig
from hermes_gateway.control_plane import (
    ControlPlane,
    HttpControlPlane,
    UnavailableControlPlane,
)
from hermes_gateway.guards import PromptDeduper, SlidingWindowRateLimiter
from hermes_gateway.hub import Connection, EventHub
from hermes_gateway.models import AgentMessage, PromptMessage, TaskDraft
from hermes_gateway.security import authenticated


def _parse_prompt(value: dict[str, Any], max_chars: int) -> str:
    try:
        if value.get("type") == "prompt":
            prompt = PromptMessage.model_validate(value).data
        else:
            prompt = AgentMessage.model_validate(value).payload.text
    except ValidationError as error:
        raise ValueError("unsupported or invalid client message") from error
    if len(prompt) > max_chars:
        raise ValueError("prompt exceeds configured character limit")
    return prompt.strip()


def _client_key(websocket: WebSocket, principal: str | None) -> str:
    host = websocket.client.host if websocket.client else "unknown"
    return hashlib.sha256(f"{principal or 'readonly'}\0{host}".encode()).hexdigest()[:16]


def create_app(
    config: GatewayConfig | None = None,
    control_plane: ControlPlane | None = None,
) -> FastAPI:
    settings = config or GatewayConfig.from_environment()
    upstream = control_plane
    if upstream is None and settings.control_plane_url:
        upstream = HttpControlPlane(
            settings.control_plane_url,
            settings.upstream_token,
            settings.upstream_poll_seconds,
        )
    upstream = upstream or UnavailableControlPlane()
    hub = EventHub(settings.buffer_size)
    limiter = SlidingWindowRateLimiter(settings.requests_per_minute)
    deduper = PromptDeduper(settings.dedupe_ttl_seconds)

    async def consume_events() -> None:
        async for event in upstream.events():
            if hub.sequence_gap(event):
                for replayed in await upstream.replay_after(None):
                    await hub.publish(replayed)
            await hub.publish(event)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        consumer = asyncio.create_task(consume_events())
        yield
        consumer.cancel()
        with suppress(asyncio.CancelledError):
            await consumer

    app = FastAPI(title="Hermes Realtime Compatibility Gateway", lifespan=lifespan)
    app.state.control_plane = upstream
    app.state.hub = hub

    @app.get("/health")
    async def health() -> dict[str, Any]:
        configured = not isinstance(upstream, UnavailableControlPlane)
        return {"status": "ready" if configured else "degraded", "canonicalSource": "control-plane"}

    @app.get("/status")
    async def wrapper_status() -> dict[str, Any]:
        try:
            wrappers = await upstream.statuses()
            return {
                "dataClass": "live",
                "wrappers": [
                    {
                        "id": item.wrapper_id,
                        "type": item.wrapper_type,
                        "status": item.status,
                        "lastSeen": int(item.last_seen.timestamp() * 1000),
                        "meta": {"name": item.wrapper_id, "type": item.wrapper_type},
                    }
                    for item in wrappers
                ],
                "frozenClientConsumesStatus": False,
            }
        except Exception:
            return {
                "dataClass": "degraded",
                "wrappers": [],
                "frozenClientConsumesStatus": False,
            }

    @app.websocket("/")
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        supplied = websocket.query_params.get("ticket") or websocket.query_params.get("token")
        can_create = authenticated(supplied, settings.client_token)
        if not can_create and not settings.allow_readonly_demo:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        requested_format = websocket.query_params.get("format", "direct")
        if requested_format not in {"direct", "canonical"}:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        connection_format = cast(Literal["direct", "canonical"], requested_format)
        connection = Connection(
            websocket=websocket,
            format=connection_format,
            read_only=not can_create,
        )
        await websocket.accept()
        hub.add(connection)
        heartbeat: asyncio.Task[None] | None = None

        async def send_heartbeats() -> None:
            while True:
                await asyncio.sleep(settings.heartbeat_seconds)
                async with connection.send_lock:
                    await websocket.send_json(
                        {
                            "type": "heartbeat",
                            "data": {"serverTime": datetime.now(UTC).isoformat()},
                            "meta": {"dataClass": "live"},
                        }
                    )

        heartbeat = asyncio.create_task(send_heartbeats())
        last_event_id = websocket.query_params.get("lastEventId")
        try:
            for event in await upstream.replay_after(last_event_id):
                await connection.send_event(event.model_copy(update={"data_class": "replayed"}))
            while True:
                raw = await websocket.receive_text()
                if len(raw.encode("utf-8")) > settings.max_message_bytes:
                    await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG)
                    return
                if connection.read_only:
                    await websocket.send_json({"type": "error", "data": "read-only demo stream"})
                    continue
                key = _client_key(websocket, supplied)
                if not limiter.allow(key):
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                try:
                    value = json.loads(raw)
                    if not isinstance(value, dict):
                        raise ValueError("message must be a JSON object")
                    prompt = _parse_prompt(value, settings.max_prompt_chars)
                except (json.JSONDecodeError, ValueError):
                    await websocket.send_json({"type": "error", "data": "invalid client message"})
                    continue
                message_id = hashlib.sha256(f"{key}\0{prompt}".encode()).hexdigest()
                existing = deduper.get(message_id)
                if existing:
                    await websocket.send_json(
                        {"type": "progress", "data": "duplicate prompt ignored", "taskId": existing}
                    )
                    continue
                draft = TaskDraft(
                    prompt=prompt,
                    clientMessageId=message_id,
                    createdAt=datetime.now(UTC),
                )
                try:
                    receipt = await upstream.create_task(draft, message_id)
                except Exception:
                    await websocket.send_json(
                        {"type": "error", "data": "canonical control plane unavailable"}
                    )
                    continue
                deduper.put(message_id, receipt.task_id)
                await websocket.send_json(
                    {"type": "progress", "data": "task accepted", "taskId": receipt.task_id}
                )
        except WebSocketDisconnect:
            pass
        finally:
            if heartbeat:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat
            hub.remove(connection)

    return app


app = create_app()
