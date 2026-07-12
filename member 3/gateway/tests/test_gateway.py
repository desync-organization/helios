from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from hermes_gateway.app import _repository_scoped_prompt, create_app
from hermes_gateway.config import GatewayConfig
from hermes_gateway.control_plane import FakeControlPlane
from hermes_gateway.models import CanonicalEvent
from hermes_gateway.projection import canonical_message, direct_message
from starlette.websockets import WebSocketDisconnect


def config(**updates: object) -> GatewayConfig:
    values: dict[str, object] = {
        "control_plane_url": None,
        "upstream_token": None,
        "client_token": "client-secret",
        "allow_readonly_demo": False,
        "max_message_bytes": 1024,
        "max_prompt_chars": 100,
        "requests_per_minute": 2,
        "dedupe_ttl_seconds": 60,
        "buffer_size": 10,
        "heartbeat_seconds": 15,
        "upstream_poll_seconds": 0.01,
    }
    values.update(updates)
    return GatewayConfig(**values)  # type: ignore[arg-type]


def event(**updates: object) -> CanonicalEvent:
    values: dict[str, object] = {
        "eventId": "event-1",
        "type": "terminal",
        "src": "runtime",
        "dst": "ui",
        "ts": 1,
        "sequence": 1,
        "taskId": "task-1",
        "runId": "run-1",
        "spanId": None,
        "payload": {"text": "working"},
        "redactionLevel": "redacted",
        "dataClass": "live",
        "persistedResultUrl": None,
    }
    values.update(updates)
    return CanonicalEvent.model_validate(values)


def test_authenticated_prompt_is_created_once() -> None:
    control_plane = FakeControlPlane()
    app = create_app(config(), control_plane)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=client-secret") as websocket:
            websocket.send_json({"type": "prompt", "data": "maintain repository"})
            assert websocket.receive_json()["data"] == "task accepted"
            websocket.send_json({"type": "prompt", "data": "maintain repository"})
            assert websocket.receive_json()["data"] == "duplicate prompt ignored"
    assert len(control_plane.created) == 1
    draft, _ = control_plane.created[0]
    assert draft.requested_actions == []
    assert draft.requires_policy_confirmation is True


def test_plain_prompt_is_scoped_to_the_configured_demo_repository() -> None:
    assert _repository_scoped_prompt(
        "Build a website",
        "https://github.com/TarunRam-git/helios-Tarun",
    ) == "Build a website\n\nRepository: https://github.com/TarunRam-git/helios-Tarun"
    explicit = "Review https://github.com/example/project/pull/1"
    assert _repository_scoped_prompt(explicit, "https://github.com/other/repo") == explicit


def test_unauthenticated_connection_is_rejected() -> None:
    app = create_app(config(), FakeControlPlane())
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as raised:
            with client.websocket_connect("/ws"):
                raise AssertionError("connection should not be accepted")
        assert raised.value.code == 1008


def test_readonly_demo_cannot_create_task() -> None:
    control_plane = FakeControlPlane()
    app = create_app(config(allow_readonly_demo=True), control_plane)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "prompt", "data": "run task"})
            assert websocket.receive_json()["data"] == "read-only demo stream"
    assert not control_plane.created


def test_invalid_message_is_rejected_without_task() -> None:
    control_plane = FakeControlPlane()
    app = create_app(config(), control_plane)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=client-secret") as websocket:
            websocket.send_json({"type": "unknown", "data": "x"})
            assert websocket.receive_json()["data"] == "invalid client message"
    assert not control_plane.created


def test_agent_envelope_is_accepted() -> None:
    control_plane = FakeControlPlane()
    app = create_app(config(), control_plane)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=client-secret") as websocket:
            websocket.send_json(
                {
                    "type": "EVENT",
                    "src": "ui-observer",
                    "dst": "pm",
                    "ts": 1780000000000,
                    "payload": {"kind": "CHAT_MESSAGE", "text": "maintain repository"},
                }
            )
            assert websocket.receive_json()["data"] == "task accepted"
    assert len(control_plane.created) == 1


def test_rate_limit_closes_abusive_client() -> None:
    app = create_app(config(requests_per_minute=1), FakeControlPlane())
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=client-secret") as websocket:
            websocket.send_json({"type": "prompt", "data": "one"})
            assert websocket.receive_json()["data"] == "task accepted"
            websocket.send_json({"type": "prompt", "data": "two"})
            with pytest.raises(WebSocketDisconnect) as raised:
                websocket.receive_json()
            assert raised.value.code == 1008


def test_oversized_message_is_closed() -> None:
    app = create_app(config(max_message_bytes=50), FakeControlPlane())
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=client-secret") as websocket:
            websocket.send_json({"type": "prompt", "data": "x" * 100})
            with pytest.raises(WebSocketDisconnect) as raised:
                websocket.receive_json()
            assert raised.value.code == 1009


def test_projection_redacts_sensitive_keys_and_values() -> None:
    projected = direct_message(
        event(
            payload={
                "text": "token ghp_abcdefghijklmnopqrstuvwxyz123456",
                "providerToken": "raw",
            }
        )
    )
    assert "ghp_" not in str(projected)
    assert "raw" not in str(projected)


def test_canonical_projection_preserves_event_identity() -> None:
    projected = canonical_message(event())
    assert projected["schemaVersion"] == "1.0"
    assert projected["eventId"] == "event-1"
    assert projected["sequence"] == 1


def test_completion_requires_live_persisted_result_url() -> None:
    values = {
        "eventId": "event-complete",
        "type": "complete",
        "src": "control-plane",
        "ts": 1,
        "sequence": 1,
        "payload": {"text": "done"},
        "redactionLevel": "redacted",
        "dataClass": "fixture",
    }
    try:
        CanonicalEvent.model_validate(values)
        raise AssertionError("fixture completion should fail")
    except ValueError as error:
        assert "cannot emit completion" in str(error)
    complete = event(
        type="complete",
        persistedResultUrl="https://github.com/example/repo/pull/1",
    )
    assert direct_message(complete)["githubUrl"].endswith("/pull/1")


def test_status_documents_frozen_client_limit() -> None:
    app = create_app(config(), FakeControlPlane())
    with TestClient(app) as client:
        response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["frozenClientConsumesStatus"] is False
