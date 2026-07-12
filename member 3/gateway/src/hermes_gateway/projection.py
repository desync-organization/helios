"""Project canonical redacted events into frozen-client direct messages."""

from __future__ import annotations

from typing import Any, cast

from hermes_gateway.models import CanonicalEvent
from hermes_gateway.security import redact


def canonical_message(event: CanonicalEvent) -> dict[str, Any]:
    return cast(dict[str, Any], redact(event.model_dump(mode="json", by_alias=True)))


def direct_message(event: CanonicalEvent) -> dict[str, Any]:
    payload = redact(event.payload)
    data: Any = payload
    if event.type in {"progress", "terminal", "cost_update", "error", "complete"}:
        data = payload.get("text", payload.get("message", ""))
    message = {
        "type": event.type,
        "data": data,
        "meta": {
            "eventId": event.event_id,
            "sequence": event.sequence,
            "taskId": event.task_id,
            "runId": event.run_id,
            "dataClass": event.data_class,
            "redactionLevel": event.redaction_level,
        },
    }
    if event.type == "complete":
        message.update(
            githubUrl=event.persisted_result_url,
            projectName=payload.get("projectName"),
            files=payload.get("files"),
        )
    return message
