import asyncio
from typing import Any

from helios.config import Settings
from helios.control_plane import ControlPlane, InMemoryControlPlane, LeaseLost
from helios.control_plane.convex_http import ConvexHttpControlPlane
from helios.control_plane.local_cache import LocalRunCache
from helios.control_plane.outbox import IdempotentOutbox
from helios.experts import default_experts
from helios.experts.model import model_backed_experts
from helios.models import ModelManager, default_model_registry
from helios.planning import PlanPolicy, Planner
from helios.planning.model_generator import LlamaPlanGenerator
from helios.scheduler import Scheduler
from helios.workspace import ArtifactStore, RepositoryNamespace


DEFAULT_TOOLS = {"repo:read", "workspace:write", "command:test", "command:cargo", "scanner:local"}


class HeliosRuntime:
    def __init__(self, settings: Settings | None = None, control_plane: ControlPlane | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.ensure_directories()
        self.control_plane = control_plane or self._control_plane()
        self.model_manager = ModelManager(default_model_registry(self.settings), self.settings.helios_max_vram_mb)
        self.experts = (model_backed_experts(self.model_manager)
                        if self.settings.helios_writeback_mode == "intent" else default_experts())
        self.plan_policy = PlanPolicy(registered_experts=set(self.experts), allowed_tools=DEFAULT_TOOLS)
        generator = LlamaPlanGenerator(self.model_manager) if self.settings.helios_writeback_mode == "intent" else None
        self.planner = Planner(self.plan_policy, generator)
        self.running = False
        self.paused = False
        self.active_runs: dict[str, str] = {}
        self.last_error: str | None = None

    def _control_plane(self) -> ControlPlane:
        if self.settings.convex_http_url:
            if not self.settings.helios_runtime_token:
                raise ValueError("HELIOS_RUNTIME_TOKEN is required with CONVEX_HTTP_URL")
        return ConvexHttpControlPlane(self.settings.convex_http_url, self.settings.helios_runtime_token,
                                      outbox=IdempotentOutbox(self.settings.helios_outbox_path))
        return InMemoryControlPlane()

    async def process_once(self) -> bool:
        if self.paused:
            return False
        lease = await self.control_plane.claim(self.settings.helios_instance_id)
        if not lease:
            return False
        task = lease.task
        task.assert_authorized()
        namespace = RepositoryNamespace(self.settings.helios_workspace_root, task.repository, task.task_id).create()
        plan, events = await self.planner.create_plan(task)
        for event in events:
            await self.control_plane.emit_event(event)
        scheduler = Scheduler(control_plane=self.control_plane, artifact_store=ArtifactStore(namespace.artifacts),
                              experts=self.experts, max_parallel=self.settings.helios_max_parallel_nodes,
                              cache=LocalRunCache(namespace.root / "state"))
        execution = asyncio.create_task(
            scheduler.execute(task, plan, lease.lease_id, run_id=task.metadata.get("resumeRunId")),
            name=f"helios-run-{task.task_id}",
        )
        heartbeat = asyncio.create_task(self._heartbeat(lease.lease_id, execution),
                                        name=f"helios-heartbeat-{task.task_id}")
        try:
            try:
                result = await execution
            except asyncio.CancelledError as exc:
                if heartbeat.done() and not heartbeat.cancelled() and heartbeat.exception():
                    raise LeaseLost("execution cancelled after heartbeat failure") from exc
                raise
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
        self.active_runs[task.task_id] = result.run_id
        return True

    async def _heartbeat(self, lease_id: str, execution: asyncio.Task) -> None:
        while not execution.done():
            await asyncio.sleep(10)
            try:
                await self.control_plane.heartbeat(lease_id)
            except Exception:
                execution.cancel()
                raise

    async def serve(self, poll_interval: float = 1.0) -> None:
        self.running = True
        try:
            while self.running:
                try:
                    worked = await self.process_once()
                    if not worked:
                        await asyncio.sleep(poll_interval)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.last_error = str(exc)[:500]
                    await asyncio.sleep(min(5, poll_interval * 2))
        finally:
            self.running = False

    def state(self) -> dict[str, Any]:
        return {"running": self.running, "paused": self.paused, "activeRuns": self.active_runs,
                "lastError": self.last_error, "writebackMode": self.settings.helios_writeback_mode}

    def stop(self) -> None:
        self.running = False
