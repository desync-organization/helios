from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from helios.contracts import Artifact, CanonicalEvent, NormalizedTask, Span
from helios.contracts.common import to_camel


class LeaseLost(RuntimeError):
    pass


class Lease(BaseModel):
    task: NormalizedTask
    lease_id: str
    expires_at: datetime


class RuntimeControlState(BaseModel):
    """Fail-safe projection of the operator controls exposed by Member 2."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    global_paused: bool = False
    emergency_mode: bool = False
    paused_agents: list[str] = Field(default_factory=list)
    writeback_mode: Literal["dry-run", "pr-only", "live"] = "dry-run"
    security_scan_mode: Literal["read-only", "remediation-approved"] = "read-only"
    current_agent_tag: str = "agents-v1"
    current_adapter_pointers: dict[str, Any] = Field(default_factory=dict)
    updated_at: int | None = None


class ControlPlane(ABC):
    @abstractmethod
    async def get_control_state(self) -> RuntimeControlState: ...

    @abstractmethod
    async def get_agent_config(self) -> dict[str, Any]: ...

    @abstractmethod
    async def resume_sequence(self, run_id: str) -> int: ...

    @abstractmethod
    async def claim(self, instance_id: str) -> Lease | None: ...

    @abstractmethod
    async def heartbeat(self, lease_id: str) -> Lease: ...

    @abstractmethod
    async def lease_valid(self, lease_id: str) -> bool: ...

    @abstractmethod
    async def emit_event(self, event: CanonicalEvent) -> None: ...

    @abstractmethod
    async def store_span(self, span: Span) -> None: ...

    @abstractmethod
    async def store_artifact(self, artifact: Artifact) -> None: ...

    @abstractmethod
    async def finish_run(self, run_id: str, result: dict[str, Any]) -> None: ...

    @abstractmethod
    async def submit_intent(self, lease_id: str, intent: Artifact) -> None: ...

    @abstractmethod
    async def escalate_task(
        self,
        lease_id: str,
        *,
        reason: str,
        run_id: str | None = None,
        artifact_ids: list[str] | None = None,
        restricted: bool = False,
    ) -> None: ...

    async def close(self) -> None:
        """Release adapter resources. In-memory implementations have nothing to close."""
