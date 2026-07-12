from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from helios.contracts import Artifact, CanonicalEvent, NormalizedTask, Span


class LeaseLost(RuntimeError):
    pass


class Lease(BaseModel):
    task: NormalizedTask
    lease_id: str
    expires_at: datetime


class ControlPlane(ABC):
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

