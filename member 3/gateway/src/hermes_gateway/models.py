"""Strict gateway protocol and control-plane adapter contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PromptMessage(ContractModel):
    type: Literal["prompt"]
    data: str = Field(min_length=1)


class AgentPayload(ContractModel):
    kind: Literal["CHAT_MESSAGE"]
    text: str = Field(min_length=1)


class AgentMessage(ContractModel):
    type: Literal["EVENT"]
    src: Literal["ui-observer"]
    dst: Literal["pm"]
    ts: int = Field(gt=0)
    payload: AgentPayload


class TaskDraft(ContractModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    prompt: str
    requested_mode: Literal["unspecified"] = Field(default="unspecified", alias="requestedMode")
    requested_actions: list[str] = Field(default_factory=list, alias="requestedActions")
    repository: None = None
    requires_policy_confirmation: Literal[True] = Field(
        default=True,
        alias="requiresPolicyConfirmation",
    )
    client_message_id: str = Field(alias="clientMessageId")
    created_at: datetime = Field(alias="createdAt")


class TaskReceipt(ContractModel):
    task_id: str = Field(alias="taskId")
    duplicate: bool = False


class CanonicalEvent(ContractModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    event_id: str = Field(alias="eventId")
    type: Literal[
        "progress",
        "terminal",
        "file",
        "token_usage",
        "cost_update",
        "complete",
        "error",
        "heartbeat",
        "snapshot",
    ]
    src: str
    dst: str = "ui"
    ts: int
    sequence: int = Field(ge=0)
    task_id: str | None = Field(default=None, alias="taskId")
    run_id: str | None = Field(default=None, alias="runId")
    span_id: str | None = Field(default=None, alias="spanId")
    payload: dict[str, Any]
    redaction_level: Literal["public", "redacted"] = Field(alias="redactionLevel")
    data_class: Literal["fixture", "dry-run", "degraded", "replayed", "live"] = Field(
        alias="dataClass"
    )
    persisted_result_url: str | None = Field(default=None, alias="persistedResultUrl")

    @model_validator(mode="after")
    def enforce_completion_truth(self) -> CanonicalEvent:
        if self.type == "complete":
            if self.data_class in {"fixture", "dry-run", "degraded"}:
                raise ValueError("fixture/dry-run/degraded events cannot emit completion")
            if not self.persisted_result_url:
                raise ValueError("completion requires a persisted result URL")
        return self


class WrapperStatus(ContractModel):
    wrapper_id: str = Field(alias="wrapperId")
    wrapper_type: str = Field(alias="wrapperType")
    status: Literal["IDLE", "THINKING", "WORKING", "BLOCKED"]
    last_seen: datetime = Field(alias="lastSeen")
