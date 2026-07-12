from __future__ import annotations

from typing import Any

import pytest
from hermes_gateway.hub import Connection, EventHub
from hermes_gateway.models import CanonicalEvent


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, value: dict[str, Any]) -> None:
        self.messages.append(value)


def canonical(sequence: int, event_id: str) -> CanonicalEvent:
    return CanonicalEvent.model_validate(
        {
            "eventId": event_id,
            "type": "progress",
            "src": "runtime",
            "ts": sequence,
            "sequence": sequence,
            "taskId": "task-1",
            "runId": "run-1",
            "payload": {"text": f"step {sequence}"},
            "redactionLevel": "redacted",
            "dataClass": "live",
        }
    )


@pytest.mark.asyncio
async def test_duplicate_and_out_of_order_events_are_not_projected_twice() -> None:
    socket = FakeWebSocket()
    hub = EventHub(buffer_size=4)
    connection = Connection(socket, "direct", False)  # type: ignore[arg-type]
    hub.add(connection)
    await hub.publish(canonical(1, "event-1"))
    await hub.publish(canonical(1, "event-duplicate-sequence"))
    await hub.publish(canonical(2, "event-2"))
    await hub.publish(canonical(2, "event-2"))
    assert [message["meta"]["sequence"] for message in socket.messages] == [1, 2]


@pytest.mark.asyncio
async def test_sequence_gap_is_detected_before_publish() -> None:
    hub = EventHub(buffer_size=4)
    assert hub.sequence_gap(canonical(1, "event-1")) is False
    await hub.publish(canonical(1, "event-1"))
    assert hub.sequence_gap(canonical(3, "event-3")) is True
