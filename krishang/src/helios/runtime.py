import asyncio
from pathlib import Path
from typing import Any

from helios.agency import AgentReservoir
from helios.config import Settings
from helios.control_plane import ControlPlane, InMemoryControlPlane, LeaseLost
from helios.control_plane.convex_http import ConvexHttpControlPlane
from helios.control_plane.local_cache import LocalRunCache
from helios.control_plane.outbox import IdempotentOutbox
from helios.models import ModelManager, default_model_registry
from helios.planning import PlanPolicy, Planner
from helios.planning.model_generator import LlamaPlanGenerator
from helios.scheduler import Scheduler
from helios.workspace import ArtifactStore, RepositoryNamespace


DEFAULT_TOOLS = {"repo:read", "workspace:write", "command:test", "command:cargo", "scanner:local", "research:proxy"}


class HeliosRuntime:
    def __init__(self, settings: Settings | None = None, control_plane: ControlPlane | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.ensure_directories()
        self.control_plane = control_plane or self._control_plane()
        self.model_manager = ModelManager(default_model_registry(self.settings), self.settings.helios_max_vram_mb)
        self._load_reservoir()
        self.running = False
        self.paused = False
        self.active_runs: dict[str, str] = {}
        self._active_execution_count = 0
        self.last_error: str | None = None

    def _catalog_path(self) -> Path:
        configured = self.settings.helios_agent_catalog
        if configured.is_file():
            return configured
        packaged = Path(__file__).resolve().parents[2] / "agents" / "baseline.yaml"
        if not packaged.is_file():
            raise FileNotFoundError(f"agent reservoir catalog not found: {configured}")
        return packaged

    def _load_reservoir(self) -> None:
        self.reservoir = AgentReservoir.from_yaml(
            self._catalog_path(), self.model_manager,
            model_backed=self.settings.helios_inference_mode == "model",
            snapshot_path=self.settings.helios_workspace_root / "agent-reservoir.json",
        )
        self.experts = self.reservoir.handlers()
        self.plan_policy = PlanPolicy(registered_experts=self.reservoir.executable_names(),
                                      allowed_tools=DEFAULT_TOOLS,
                                      agent_catalog=self.reservoir.planner_catalog())
        generator = LlamaPlanGenerator(self.model_manager) if self.settings.helios_inference_mode == "model" else None
        self.planner = Planner(self.plan_policy, generator, self.reservoir.planner_catalog)

    def reload_reservoir(self) -> dict[str, Any]:
        if self._active_execution_count:
            raise RuntimeError("agent reservoir reload is blocked while runs are active")
        self._load_reservoir()
        return {"agents": len(self.reservoir.list()), "executable": len(self.reservoir.executable_names())}

    def _control_plane(self) -> ControlPlane:
        if self.settings.convex_http_url:
            if not self.settings.helios_runtime_token:
                raise ValueError("HELIOS_RUNTIME_TOKEN is required with CONVEX_HTTP_URL")
            return ConvexHttpControlPlane(
                self.settings.convex_http_url,
                self.settings.helios_runtime_token,
                outbox=IdempotentOutbox(self.settings.helios_outbox_path),
            )
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
                              cache=LocalRunCache(namespace.root / "state"), reservoir=self.reservoir)
        execution = asyncio.create_task(
            scheduler.execute(task, plan, lease.lease_id, run_id=task.metadata.get("resumeRunId")),
            name=f"helios-run-{task.task_id}",
        )
        heartbeat = asyncio.create_task(self._heartbeat(lease.lease_id, execution),
                                        name=f"helios-heartbeat-{task.task_id}")
        self._active_execution_count += 1
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
            self._active_execution_count -= 1
        self.active_runs[task.task_id] = result.run_id
        self.experts = self.reservoir.handlers()
        self.plan_policy.registered_experts = self.reservoir.executable_names()
        self.plan_policy.agent_catalog = self.reservoir.planner_catalog()
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
                "lastError": self.last_error, "writebackMode": self.settings.helios_writeback_mode,
                "agentReservoir": {"total": len(self.reservoir.list()),
                                   "executable": len(self.reservoir.executable_names()),
                                   "revision": self.reservoir.revision}}

    def stop(self) -> None:
        self.running = False
