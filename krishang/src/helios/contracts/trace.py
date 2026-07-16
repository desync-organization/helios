from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from helios.clock import now_utc
from helios.ids import new_id
from .common import WireModel


class RedactionLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SECRET_REDACTED = "secret_redacted"


class CanonicalEvent(WireModel):
    schema_version: str = "1.0"
    event_id: str = Field(default_factory=lambda: new_id("event"))
    type: str
    source: str = "helios-runtime"
    timestamp: datetime = Field(default_factory=now_utc)
    sequence: int = 0
    task_id: str | None = None
    run_id: str | None = None
    span_id: str | None = None
    label: Literal["live", "dry-run", "degraded", "replayed", "fixture"] = "live"
    payload: dict[str, Any] = Field(default_factory=dict)
    redaction_level: RedactionLevel = RedactionLevel.INTERNAL


class Span(WireModel):
    schema_version: str = "1.0"
    span_id: str = Field(default_factory=lambda: new_id("span"))
    run_id: str
    task_id: str
    parent_span_id: str | None = None
    node_id: str
    agent: str
    agent_version: str = "1.0"
    model: str = "deterministic"
    prompt_hash: str = ""
    input_artifact_refs: list[str] = Field(default_factory=list)
    output_artifact_ref: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0
    cost_cloud_equiv_usd: float = 0
    latency_ms: float = 0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    verdict: str | None = None
    error: str | None = None
    degraded: bool = False
