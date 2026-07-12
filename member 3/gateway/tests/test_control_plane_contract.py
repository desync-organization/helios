from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from hermes_gateway.control_plane import HttpControlPlane
from hermes_gateway.models import TaskDraft


@pytest.mark.asyncio
async def test_member2_gateway_http_contract() -> None:
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["authorization"] == "Bearer gateway-token"
        if request.url.path == "/gateway/task-drafts":
            assert request.headers["idempotency-key"] == "client-message-id"
            assert json.loads(request.content)["prompt"].endswith("/issues/7")
            return httpx.Response(
                200,
                json={"taskId": "tsk_01J00000000000000000000000", "duplicate": False},
            )
        if request.url.path == "/gateway/events":
            return httpx.Response(200, json=[{
                "schemaVersion": "1.0",
                "eventId": "evt_01J00000000000000000000000",
                "type": "progress",
                "src": "runtime",
                "dst": "ui",
                "ts": 1,
                "sequence": 1,
                "taskId": "tsk_01J00000000000000000000000",
                "runId": "run_01J00000000000000000000000",
                "spanId": None,
                "payload": {"text": "run started"},
                "redactionLevel": "redacted",
                "dataClass": "live",
                "persistedResultUrl": None,
            }])
        if request.url.path == "/gateway/status":
            return httpx.Response(200, json=[{
                "wrapperId": "helios-runtime",
                "wrapperType": "runtime",
                "status": "WORKING",
                "lastSeen": "2026-07-12T00:00:00Z",
            }])
        return httpx.Response(404)

    control = HttpControlPlane(
        "https://control.example",
        "gateway-token",
        0.01,
        transport=httpx.MockTransport(handler),
    )
    draft = TaskDraft(
        prompt="https://github.com/owner/repo/issues/7",
        clientMessageId="client-message-id",
        createdAt=datetime(2026, 7, 12, tzinfo=UTC),
    )
    receipt = await control.create_task(draft, "client-message-id")
    events = await control.replay_after(None)
    statuses = await control.statuses()

    assert receipt.task_id.startswith("tsk_")
    assert events[0].payload["text"] == "run started"
    assert statuses[0].status == "WORKING"
    assert [request.url.path for request in calls] == [
        "/gateway/task-drafts",
        "/gateway/events",
        "/gateway/status",
    ]
