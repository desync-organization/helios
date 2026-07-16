import asyncio
from datetime import timedelta
from typing import Any

from helios.clock import now_utc
from helios.contracts import Artifact, CanonicalEvent, NormalizedTask, Span
from helios.ids import new_id

from .base import ControlPlane, Lease, LeaseLost, RuntimeControlState


class InMemoryControlPlane(ControlPlane):
    def __init__(self, lease_seconds: int = 120) -> None:
        self.tasks: asyncio.Queue[NormalizedTask] = asyncio.Queue()
        self.leases: dict[str, Lease] = {}
        self.events: dict[str, CanonicalEvent] = {}
        self.spans: dict[str, Span] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.intents: dict[str, Artifact] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self.escalations: dict[str, dict[str, Any]] = {}
        self.control_state = RuntimeControlState()
        self.agent_config: dict[str, Any] = {"agents": [], "adapters": {}}
        self.lease_seconds = lease_seconds

    async def get_control_state(self) -> RuntimeControlState:
        return self.control_state.model_copy(deep=True)

    async def get_agent_config(self) -> dict[str, Any]:
        return {
            "agents": [dict(item) for item in self.agent_config.get("agents", [])],
            "adapters": dict(self.agent_config.get("adapters", {})),
        }

    async def resume_sequence(self, run_id: str) -> int:
        return max(
            (event.sequence for event in self.events.values() if event.run_id == run_id),
            default=0,
        )

    async def enqueue(self, task: NormalizedTask) -> None:
        await self.tasks.put(task)

    async def claim(self, instance_id: str) -> Lease | None:
        del instance_id
        try:
            task = self.tasks.get_nowait()
        except asyncio.QueueEmpty:
            return None
        lease = Lease(
            task=task,
            lease_id=new_id("lease"),
            expires_at=now_utc() + timedelta(seconds=self.lease_seconds),
        )
        self.leases[lease.lease_id] = lease
        return lease

    async def heartbeat(self, lease_id: str) -> Lease:
        if not await self.lease_valid(lease_id):
            raise LeaseLost("lease expired or missing")
        lease = self.leases[lease_id]
        lease.expires_at = now_utc() + timedelta(seconds=self.lease_seconds)
        return lease

    async def lease_valid(self, lease_id: str) -> bool:
        lease = self.leases.get(lease_id)
        return bool(lease and lease.expires_at > now_utc())

    async def emit_event(self, event: CanonicalEvent) -> None:
        self.events.setdefault(event.event_id, event)

    async def store_span(self, span: Span) -> None:
        self.spans.setdefault(span.span_id, span)

    async def store_artifact(self, artifact: Artifact) -> None:
        self.artifacts.setdefault(artifact.artifact_id, artifact)

    async def finish_run(self, run_id: str, result: dict[str, Any]) -> None:
        self.results.setdefault(run_id, result)

    async def submit_intent(self, lease_id: str, intent: Artifact) -> None:
        if not await self.lease_valid(lease_id):
            raise LeaseLost("write-back cancelled because lease is invalid")
        self.intents.setdefault(intent.artifact_id, intent)

    async def escalate_task(
        self,
        lease_id: str,
        *,
        reason: str,
        run_id: str | None = None,
        artifact_ids: list[str] | None = None,
        restricted: bool = False,
    ) -> None:
        state = self.leases.get(lease_id)
        if not state:
            raise LeaseLost("cannot escalate an unknown lease")
        self.escalations.setdefault(lease_id, {
            "taskId": state.task.task_id,
            "runId": run_id,
            "artifactIds": list(artifact_ids or []),
            "reason": reason[:500],
            "restricted": restricted,
        })
        if run_id:
            self.results.setdefault(run_id, {"status": "escalated", "reason": reason[:500]})
        self.leases.pop(lease_id, None)
