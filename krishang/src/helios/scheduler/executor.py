import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from helios.contracts import Artifact, ArtifactType, CanonicalEvent, NormalizedTask, Plan, Span
from helios.contracts.plan import NodeKind, PlanNode
from helios.control_plane import ControlPlane, LeaseLost
from helios.control_plane.local_cache import LocalRunCache
from helios.experts import ExpertContext, ExpertHandler
from helios.ids import new_id
from helios.security.redaction import redact
from helios.workspace import ArtifactStore

from .budgets import BudgetExceeded, enforce_usage
from .dag import execution_layers
from .resume import save_progress
from .retry import RevisionState


@dataclass(slots=True)
class ExecutionResult:
    run_id: str
    status: str
    artifacts: dict[str, Artifact]
    intent: Artifact | None
    events: list[CanonicalEvent] = field(default_factory=list)
    latency_ms: float = 0
    actual_cost_usd: float = 0


class Scheduler:
    def __init__(self, *, control_plane: ControlPlane, artifact_store: ArtifactStore,
                 experts: dict[str, ExpertHandler], max_parallel: int = 3,
                 cache: LocalRunCache | None = None) -> None:
        self.control_plane = control_plane
        self.artifact_store = artifact_store
        self.experts = experts
        self.semaphore = asyncio.Semaphore(max_parallel)
        self.event_lock = asyncio.Lock()
        self.cache = cache
        self.sequence = 0

    async def _event(self, event_type: str, task: NormalizedTask, run_id: str, payload: dict[str, Any],
                     span_id: str | None = None) -> CanonicalEvent:
        async with self.event_lock:
            self.sequence += 1
            event = CanonicalEvent(type=event_type, task_id=task.task_id, run_id=run_id, span_id=span_id,
                                   sequence=self.sequence, payload=redact(payload))
            await self.control_plane.emit_event(event)
            return event

    async def _run_node(self, task: NormalizedTask, run_id: str, node: PlanNode,
                        artifacts: dict[str, Artifact], revision_notes: list[str]) -> tuple[Artifact, Span, list[CanonicalEvent]]:
        handler = self.experts.get(node.expert)
        if not handler:
            raise ValueError(f"no handler registered for {node.expert}")
        upstream = [artifacts[item] for item in node.dependencies]
        started = time.perf_counter()
        span = Span(run_id=run_id, task_id=task.task_id, node_id=node.node_id, agent=node.expert,
                    input_artifact_refs=[item.artifact_id for item in upstream])
        events = [await self._event("plan_node_started", task, run_id, {"nodeId": node.node_id, "agent": node.expert}, span.span_id)]
        try:
            async with self.semaphore:
                content = await asyncio.wait_for(
                    handler(ExpertContext(task=task, run_id=run_id, node=node, upstream=upstream, revision_notes=revision_notes)),
                    timeout=node.budget.max_seconds,
                )
            usage = content.pop("_usage", {"tokens": 0, "costUsd": 0})
            enforce_usage(tokens=int(usage.get("tokens", 0)), cost_usd=float(usage.get("costUsd", 0)),
                          max_tokens=node.budget.max_tokens, max_cost_usd=node.budget.max_cost_usd)
            artifact = Artifact.create(task_id=task.task_id, run_id=run_id,
                                       artifact_type=ArtifactType(node.output_artifact), producer=node.expert,
                                       upstream_artifact_ids=[item.artifact_id for item in upstream],
                                       policy_ids=node.policy_ids, content=redact(content))
            self.artifact_store.put(artifact)
            await self.control_plane.store_artifact(artifact)
            span.output_artifact_ref = artifact.artifact_id
            span.tokens_out = int(usage.get("tokens", 0))
            span.cost_usd = float(usage.get("costUsd", 0))
            if artifact.artifact_type == ArtifactType.CRITIC_VERDICT:
                span.verdict = str(artifact.content.get("verdict"))
            events.append(await self._event("artifact_created", task, run_id,
                                            {"nodeId": node.node_id, "artifactId": artifact.artifact_id,
                                             "artifactType": artifact.artifact_type.value}, span.span_id))
        except (TimeoutError, BudgetExceeded, Exception) as exc:
            span.error = str(exc)[:500]
            span.latency_ms = (time.perf_counter() - started) * 1000
            await self.control_plane.store_span(span)
            await self._event("plan_node_failed", task, run_id, {"nodeId": node.node_id, "error": span.error}, span.span_id)
            raise
        span.latency_ms = (time.perf_counter() - started) * 1000
        await self.control_plane.store_span(span)
        events.append(await self._event("plan_node_completed", task, run_id,
                                        {"nodeId": node.node_id, "latencyMs": span.latency_ms}, span.span_id))
        return artifact, span, events

    async def execute(self, task: NormalizedTask, plan: Plan, lease_id: str, *, run_id: str | None = None) -> ExecutionResult:
        run_id = run_id or new_id("run")
        artifacts: dict[str, Artifact] = {}
        run_started = time.perf_counter()
        total_cost = 0.0
        events: list[CanonicalEvent] = [await self._event("run_started", task, run_id, {"planId": plan.plan_id})]
        completed: set[str] = set()
        if self.cache and run_id:
            state = self.cache.load(run_id)
            if state:
                for node_id, artifact_id in state.get("artifacts", {}).items():
                    artifacts[node_id] = self.artifact_store.get(artifact_id)
                completed = set(state.get("completedNodes", [])) & set(artifacts)
        revisions = RevisionState()
        nodes = {node.node_id: node for node in plan.nodes}
        try:
            for layer in execution_layers(plan):
                runnable = [node_id for node_id in layer if node_id not in completed]
                results = await asyncio.gather(*[
                    self._run_node(task, run_id, nodes[node_id], artifacts, []) for node_id in runnable
                ])
                for node_id, (artifact, _, node_events) in zip(runnable, results, strict=True):
                    artifacts[node_id] = artifact
                    completed.add(node_id)
                    events.extend(node_events)
                total_cost += sum(span.cost_usd for _, span, _ in results)
                save_progress(self.cache, run_id, completed, {key: value.artifact_id for key, value in artifacts.items()})

                for node_id in runnable:
                    node = nodes[node_id]
                    artifact = artifacts[node_id]
                    if node.kind == NodeKind.CRITIC and artifact.content.get("verdict") == "revise":
                        notes = list(artifact.content.get("notes", []))
                        if revisions.permit(notes):
                            for dependency in node.dependencies:
                                replacement, _, extra = await self._run_node(task, run_id, nodes[dependency], artifacts, notes)
                                artifacts[dependency] = replacement
                                events.extend(extra)
                            replacement, _, extra = await self._run_node(task, run_id, node, artifacts, notes)
                            artifacts[node_id] = replacement
                            events.extend(extra)
                        if artifacts[node_id].content.get("verdict") != "pass":
                            escalation = Artifact.create(task_id=task.task_id, run_id=run_id,
                                artifact_type=ArtifactType.ESCALATION, producer="scheduler",
                                upstream_artifact_ids=[item.artifact_id for item in artifacts.values()],
                                policy_ids=["runtime.two-critic-rejections"],
                                content={"whatITried": "one critic-directed revision", "exactFailure": notes,
                                         "smallestFailingCase": task.title,
                                         "artifactChain": [item.artifact_id for item in artifacts.values()],
                                         "decisionNeeded": "human review required"})
                            self.artifact_store.put(escalation)
                            await self.control_plane.store_artifact(escalation)
                            artifacts["escalation"] = escalation

            intent = artifacts.get(plan.terminal_node_id)
            if intent and intent.content.get("authorized"):
                if not await self.control_plane.lease_valid(lease_id):
                    raise LeaseLost("lease lost before write-back")
                await self.control_plane.submit_intent(lease_id, intent)
            status = "completed" if intent and intent.content.get("authorized") else "escalated"
            latency_ms = (time.perf_counter() - run_started) * 1000
            events.append(await self._event("run_finished", task, run_id, {"status": status}))
            await self.control_plane.finish_run(run_id, {"status": status, "intentId": intent.artifact_id if intent else None,
                                                         "latencyMs": latency_ms, "actualCostUsd": total_cost})
            return ExecutionResult(run_id=run_id, status=status, artifacts=artifacts, intent=intent,
                                   events=events, latency_ms=latency_ms, actual_cost_usd=total_cost)
        except Exception as exc:
            events.append(await self._event("run_failed", task, run_id, {"error": str(exc)[:500]}))
            await self.control_plane.finish_run(run_id, {"status": "failed", "error": str(exc)[:500]})
            raise
