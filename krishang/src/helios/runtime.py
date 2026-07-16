import asyncio
from contextlib import suppress
from pathlib import Path
import time
from typing import Any

from helios.agency import AgentReservoir
from helios.config import Settings
from helios.contracts import CanonicalEvent, NormalizedTask
from helios.control_plane import ControlPlane, InMemoryControlPlane, LeaseLost, RuntimeControlState
from helios.control_plane.convex_http import ConvexHttpControlPlane
from helios.control_plane.local_cache import LocalRunCache
from helios.control_plane.outbox import IdempotentOutbox
from helios.execution import ExecutionServices
from helios.models import ModelManager, default_model_registry
from helios.planning import PlanPolicy, Planner
from helios.planning.model_generator import LlamaPlanGenerator
from helios.scheduler import Scheduler
from helios.ids import new_id
from helios.security.redaction import redact
from helios.workspace import ArtifactStore, RepositoryNamespace, prepare_repository_build


DEFAULT_TOOLS = {"repo:read", "workspace:write", "command:test", "command:cargo", "scanner:local", "research:proxy"}


class HeliosRuntime:
    def __init__(
        self,
        settings: Settings | None = None,
        control_plane: ControlPlane | None = None,
        *,
        source_repositories: dict[str, Path] | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.settings.ensure_directories()
        self.control_plane = control_plane or self._control_plane()
        self.source_repositories = {
            repository: path.resolve()
            for repository, path in (source_repositories or {}).items()
        }
        self.model_manager = ModelManager(default_model_registry(self.settings), self.settings.helios_max_vram_mb)
        self._load_reservoir()
        self.remote_control = RuntimeControlState()
        self._remote_paused_agents: set[str] = set()
        self.remote_agent_config: dict[str, Any] = {"agents": [], "adapters": {}}
        self.remote_agent_mismatches: list[str] = []
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
        catalog = self._planner_catalog()
        self.plan_policy = PlanPolicy(registered_experts=self.reservoir.executable_names(),
                                      allowed_tools=DEFAULT_TOOLS,
                                      agent_catalog=catalog)
        generator = LlamaPlanGenerator(self.model_manager) if self.settings.helios_inference_mode == "model" else None
        self.planner = Planner(self.plan_policy, generator, self._planner_catalog)

    def _planner_catalog(self) -> list[dict[str, Any]]:
        paused = getattr(self, "_remote_paused_agents", set())
        remote_agents = {
            str(item.get("name")): item
            for item in getattr(self, "remote_agent_config", {}).get("agents", [])
            if isinstance(item, dict) and item.get("name")
        }
        catalog: list[dict[str, Any]] = []
        for item in self.reservoir.planner_catalog():
            projected = dict(item)
            if projected["name"] in paused:
                projected["status"] = "paused"
            remote = remote_agents.get(projected["name"])
            if remote:
                projected["controlPlaneVersion"] = remote.get("version")
                projected["controlPlaneAdapterId"] = remote.get("activeAdapterId")
            catalog.append(projected)
        return catalog

    def _apply_control_state(self, state: RuntimeControlState) -> None:
        self.remote_control = state
        self._remote_paused_agents = set(state.paused_agents)
        self.plan_policy.registered_experts = self.reservoir.executable_names() - self._remote_paused_agents
        self.plan_policy.agent_catalog = self._planner_catalog()

    def _apply_agent_config(self, config: dict[str, Any]) -> None:
        local = {definition.name: definition for definition in self.reservoir.list()}
        mismatches: list[str] = []
        for item in config.get("agents", []):
            if not isinstance(item, dict) or not item.get("name"):
                mismatches.append("malformed remote agent record")
                continue
            name = str(item["name"])
            definition = local.get(name)
            if not definition:
                mismatches.append(f"remote agent is not locally executable: {name}")
                continue
            grants = item.get("toolGrants", [])
            if not isinstance(grants, list) or set(map(str, grants)) - set(definition.tools):
                mismatches.append(f"remote tool grants exceed local policy: {name}")
            model_identity = item.get("modelIdentity", {})
            remote_model = model_identity.get("modelId") if isinstance(model_identity, dict) else None
            if remote_model and remote_model != definition.model_id:
                mismatches.append(f"remote model identity differs from local catalog: {name}")
        self.remote_agent_config = config
        self.remote_agent_mismatches = mismatches
        self.plan_policy.agent_catalog = self._planner_catalog()

    def reload_reservoir(self) -> dict[str, Any]:
        if self._active_execution_count:
            raise RuntimeError("agent reservoir reload is blocked while runs are active")
        self._load_reservoir()
        return {"agents": len(self.reservoir.list()), "executable": len(self.reservoir.executable_names())}

    def _control_plane(self) -> ControlPlane:
        if self.settings.runtime_control_plane_url:
            if not self.settings.helios_runtime_token:
                raise ValueError("RUNTIME_BEARER_TOKEN is required with the runtime control-plane URL")
            return ConvexHttpControlPlane(
                self.settings.runtime_control_plane_url,
                self.settings.helios_runtime_token,
                outbox=IdempotentOutbox(self.settings.helios_outbox_path),
            )
        return InMemoryControlPlane()

    async def process_once(self) -> bool:
        if self.paused:
            return False
        self._apply_control_state(await self.control_plane.get_control_state())
        self._apply_agent_config(await self.control_plane.get_agent_config())
        if self.remote_control.global_paused or self.remote_control.emergency_mode:
            return False
        lease = await self.control_plane.claim(self.settings.helios_instance_id)
        if not lease:
            return False
        task = lease.task
        deadline = time.perf_counter() + task.consent.max_runtime_s
        resume_run_id = task.metadata.get("resumeRunId")
        run_id = str(resume_run_id) if isinstance(resume_run_id, str) and resume_run_id else new_id("run")
        work = asyncio.create_task(
            self._process_lease(
                task,
                lease.lease_id,
                run_id,
                resume=bool(resume_run_id),
                deadline=deadline,
            ),
            name=f"helios-run-{task.task_id}",
        )
        heartbeat = asyncio.create_task(
            self._heartbeat(lease.lease_id, run_id, work),
            name=f"helios-heartbeat-{task.task_id}",
        )
        self._active_execution_count += 1
        try:
            try:
                result = await work
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
        self._apply_control_state(self.remote_control)
        return True

    async def _process_lease(
        self,
        task: NormalizedTask,
        lease_id: str,
        run_id: str,
        *,
        resume: bool = False,
        deadline: float | None = None,
    ):
        sequence = 0
        scheduler_started = False
        event_label = (
            "dry-run"
            if self.settings.helios_writeback_mode == "dry-run"
            or self.remote_control.writeback_mode == "dry-run"
            else "live"
        )
        try:
            if resume:
                sequence = await self.control_plane.resume_sequence(run_id)
            sequence += 1
            await self.control_plane.emit_event(CanonicalEvent(
                type="task_claimed",
                task_id=task.task_id,
                run_id=run_id,
                sequence=sequence,
                label=event_label,
                payload={"mode": task.mode.value, "taskType": task.task_type.value, "repository": task.repository},
            ))
            task.assert_authorized()
            if (task.mode.value == "security_audit" and task.task_type.value == "remediate"
                    and self.remote_control.security_scan_mode == "read-only"):
                raise PermissionError("remote control permits read-only security scans, not remediation")
            namespace = RepositoryNamespace(self.settings.helios_workspace_root, task.repository, task.task_id).create()
            if (
                task.mode.value == "build"
                and task.source == "github"
                and str(task.metadata.get("sourceUrl", "")).startswith("https://github.com/")
                and not task.metadata.get("proposedFiles")
                and task.repository not in self.source_repositories
            ):
                remaining = (deadline - time.perf_counter()) if deadline else task.consent.max_runtime_s
                if remaining <= 0:
                    raise TimeoutError("task runtime budget was exhausted before repository preparation")
                await asyncio.wait_for(prepare_repository_build(task, namespace.root), timeout=remaining)
            remaining = (deadline - time.perf_counter()) if deadline else task.consent.max_runtime_s
            if remaining <= 0:
                raise TimeoutError("task runtime budget was exhausted before planning")
            plan, events = await asyncio.wait_for(self.planner.create_plan(task), timeout=remaining)
            for event in events:
                sequence += 1
                event.run_id = run_id
                event.task_id = task.task_id
                event.sequence = sequence
                event.label = event_label
                event.payload = redact(event.payload)
                await self.control_plane.emit_event(event)
            writeback_enabled = (
                self.settings.helios_writeback_mode == "intent"
                and self.remote_control.writeback_mode != "dry-run"
                and not self.remote_control.global_paused
                and not self.remote_control.emergency_mode
            )
            scheduler = Scheduler(
                control_plane=self.control_plane,
                artifact_store=ArtifactStore(namespace.artifacts),
                experts=self.experts,
                max_parallel=self.settings.helios_max_parallel_nodes,
                cache=LocalRunCache(namespace.root / "state"),
                reservoir=self.reservoir,
                execution_services=ExecutionServices(
                    task,
                    namespace.root,
                    source_repository=self.source_repositories.get(task.repository),
                ),
                writeback_enabled=writeback_enabled,
                writeback_mode=self.remote_control.writeback_mode,
                event_label=event_label,
                initial_sequence=sequence,
            )
            scheduler_started = True
            return await scheduler.execute(task, plan, lease_id, run_id=run_id, deadline=deadline)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not scheduler_started:
                sequence += 1
                with suppress(Exception):
                    await self.control_plane.emit_event(CanonicalEvent(
                        type="run_preflight_failed",
                        task_id=task.task_id,
                        run_id=run_id,
                        sequence=sequence,
                        label=event_label,
                        payload={"error": redact(str(exc)[:500])},
                    ))
                status = "escalated" if isinstance(exc, (PermissionError, ValueError)) else "failed"
                try:
                    await self.control_plane.finish_run(
                        run_id,
                        {"status": status, "error": redact(str(exc)[:500])},
                    )
                except Exception:
                    with suppress(Exception):
                        await self.control_plane.escalate_task(
                            lease_id,
                            reason=redact(str(exc)[:500]),
                            run_id=run_id,
                        )
            raise

    async def _heartbeat(self, lease_id: str, run_id: str, execution: asyncio.Task) -> None:
        while not execution.done():
            await asyncio.sleep(10)
            try:
                await self.control_plane.heartbeat(lease_id)
                controls = await self.control_plane.get_control_state()
                self._apply_control_state(controls)
                if controls.global_paused or controls.emergency_mode:
                    reason = (
                        "runtime cancelled by emergency mode"
                        if controls.emergency_mode
                        else "runtime cancelled by global pause"
                    )
                    execution.cancel()
                    with suppress(Exception):
                        await self.control_plane.escalate_task(
                            lease_id,
                            reason=reason,
                            run_id=run_id,
                        )
                    raise RuntimeError(reason)
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
                    self.last_error = str(redact(str(exc)[:500]))
                    await asyncio.sleep(min(5, poll_interval * 2))
        finally:
            self.running = False
            await self.control_plane.close()

    def state(self) -> dict[str, Any]:
        effective_writeback = "dry-run" if self.settings.helios_writeback_mode == "dry-run" else self.remote_control.writeback_mode
        return {"running": self.running, "paused": self.paused, "activeRuns": self.active_runs,
                "lastError": self.last_error, "writebackMode": effective_writeback,
                "remoteControl": self.remote_control.model_dump(mode="json", by_alias=True),
                "controlPlaneRegistry": {
                    "agents": len(self.remote_agent_config.get("agents", [])),
                    "adapterPointers": self.remote_agent_config.get("adapters", {}),
                    "mismatches": self.remote_agent_mismatches,
                },
                "agentReservoir": {"total": len(self.reservoir.list()),
                                   "executable": len(self.reservoir.executable_names()),
                                   "revision": self.reservoir.revision}}

    def stop(self) -> None:
        self.running = False
