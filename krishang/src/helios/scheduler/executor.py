import asyncio
import hashlib
import json
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from helios.agency.head import HeadOrchestratorValidator
from helios.agency.reservoir import AgentReservoir
from helios.contracts import Artifact, ArtifactType, CanonicalEvent, NormalizedTask, Plan, Span
from helios.contracts.plan import NodeKind, PlanNode
from helios.control_plane import ControlPlane, LeaseLost
from helios.control_plane.local_cache import LocalRunCache
from helios.execution import ExecutionServices
from helios.experts import ExpertContext, ExpertHandler
from helios.ids import new_id
from helios.security.redaction import redact
from helios.workspace import ArtifactStore

from .budgets import enforce_usage
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
                 cache: LocalRunCache | None = None,
                 reservoir: AgentReservoir | None = None,
                 execution_services: ExecutionServices | None = None,
                 writeback_enabled: bool = False,
                 writeback_mode: str = "live",
                 event_label: str = "live",
                 initial_sequence: int = 0) -> None:
        self.control_plane = control_plane
        self.artifact_store = artifact_store
        self.experts = experts
        self.semaphore = asyncio.Semaphore(max_parallel)
        self.event_lock = asyncio.Lock()
        self.cache = cache
        self.reservoir = reservoir
        self.execution_services = execution_services
        self.writeback_enabled = writeback_enabled
        if writeback_mode not in {"dry-run", "pr-only", "live"}:
            raise ValueError("unsupported scheduler write-back mode")
        self.writeback_mode = writeback_mode
        if event_label not in {"live", "dry-run", "degraded", "replayed", "fixture"}:
            raise ValueError("unsupported event label")
        self.event_label = event_label
        self.head_validator = HeadOrchestratorValidator()
        self.sequence = initial_sequence

    async def _event(self, event_type: str, task: NormalizedTask, run_id: str, payload: dict[str, Any],
                     span_id: str | None = None) -> CanonicalEvent:
        async with self.event_lock:
            self.sequence += 1
            event = CanonicalEvent(type=event_type, task_id=task.task_id, run_id=run_id, span_id=span_id,
                                   sequence=self.sequence, label=self.event_label, payload=redact(payload))
            await self.control_plane.emit_event(event)
            return event

    async def _record_failure(self, events: list[CanonicalEvent], task: NormalizedTask,
                              run_id: str, lease_id: str, exc: Exception) -> None:
        failure = {"status": "failed", "error": redact(str(exc)[:500])}
        with suppress(Exception):
            events.append(await self._event("run_failed", task, run_id, {"error": failure["error"]}))
        # Finalization is deliberately independent from event delivery. A sequence
        # conflict or disconnected event sink must not leave the canonical run open.
        try:
            await self.control_plane.finish_run(run_id, failure)
        except Exception:
            with suppress(Exception):
                await self.control_plane.escalate_task(
                    lease_id,
                    reason=failure["error"],
                    run_id=run_id,
                )

    async def _store_escalation(self, task: NormalizedTask, run_id: str,
                                artifacts: dict[str, Artifact], notes: list[str],
                                what_i_tried: str) -> Artifact:
        escalation = Artifact.create(
            task_id=task.task_id,
            run_id=run_id,
            artifact_type=ArtifactType.ESCALATION,
            producer="scheduler",
            upstream_artifact_ids=[item.artifact_id for item in artifacts.values()],
            policy_ids=["runtime.critic-escalation"],
            content={
                "whatITried": what_i_tried,
                "exactFailure": notes,
                "smallestFailingCase": task.title,
                "artifactChain": [item.artifact_id for item in artifacts.values()],
                "decisionNeeded": "human review required",
            },
        )
        self.artifact_store.put(escalation)
        await self.control_plane.store_artifact(escalation)
        artifacts["escalation"] = escalation
        return escalation

    async def _run_node(self, task: NormalizedTask, run_id: str, node: PlanNode,
                        artifacts: dict[str, Artifact], revision_notes: list[str],
                        execution_services: ExecutionServices,
                        deadline: float) -> tuple[Artifact, Span, list[CanonicalEvent]]:
        handler = self.experts.get(node.expert)
        spawn_event: CanonicalEvent | None = None
        if not handler and node.spawn and self.reservoir:
            _, spawn_event = self.reservoir.spawn(
                node.spawn,
                run_id=run_id,
                budget_tokens=node.budget.max_tokens,
                budget_seconds=node.budget.max_seconds,
                allowed_tools=set(node.tool_grants),
            )
            handler = self.reservoir.handler(node.expert)
            if handler:
                self.experts[node.expert] = handler
        if not handler:
            raise ValueError(f"no handler registered for {node.expert}")
        upstream = [artifacts[item] for item in node.dependencies]
        started = time.perf_counter()
        span = Span(run_id=run_id, task_id=task.task_id, node_id=node.node_id, agent=node.expert,
                    input_artifact_refs=[item.artifact_id for item in upstream])
        events: list[CanonicalEvent] = []
        if spawn_event:
            events.append(await self._event(
                spawn_event.type,
                task,
                run_id,
                spawn_event.payload,
                span.span_id,
            ))
        events.append(await self._event("plan_node_started", task, run_id,
                                        {"nodeId": node.node_id, "agent": node.expert}, span.span_id))
        try:
            node_execution = execution_services.for_node(node)
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("task consent runtime budget was exhausted")
            async with self.semaphore:
                content = await asyncio.wait_for(
                    handler(ExpertContext(
                        task=task,
                        run_id=run_id,
                        node=node,
                        upstream=upstream,
                        revision_notes=revision_notes,
                        execution=node_execution,
                    )),
                    timeout=min(node.budget.max_seconds, remaining),
                )
            if not isinstance(content, dict):
                raise TypeError("expert handler must return a JSON object")
            usage = content.pop("_usage", {"tokens": 0, "costUsd": 0})
            model_provenance = content.pop("_model", None)
            enforce_usage(tokens=int(usage.get("tokens", 0)), cost_usd=float(usage.get("costUsd", 0)),
                          max_tokens=node.budget.max_tokens, max_cost_usd=node.budget.max_cost_usd)
            scope_checks = node_execution.validate_output_scope(content)
            original_files = content.get("files") if isinstance(content.get("files"), list) else None
            content = redact(content)
            if original_files is not None:
                # Source bytes are validated and blocked on high-confidence secrets;
                # they must never be rewritten by telemetry-oriented redaction.
                content["files"] = original_files
            if model_provenance:
                content["modelProvenance"] = model_provenance
                span.model = str(model_provenance.get("baseModel", "unknown"))
            head_validation = self.head_validator.validate(node, content, upstream)
            materialization = await node_execution.commit_validated_output(content)
            if materialization:
                content["executionEvidence"] = materialization
            head_validation.checks.extend(scope_checks)
            content["headValidation"] = {
                "valid": head_validation.valid,
                "checks": head_validation.checks,
                "summary": head_validation.summary,
            }
            artifact = Artifact.create(task_id=task.task_id, run_id=run_id,
                                       artifact_type=ArtifactType(node.output_artifact), producer=node.expert,
                                       upstream_artifact_ids=[item.artifact_id for item in upstream],
                                       policy_ids=node.policy_ids, content=content)
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
            events.append(await self._event("head_validation_passed", task, run_id,
                                            {"nodeId": node.node_id, "agent": node.expert,
                                             "checks": head_validation.checks,
                                             "artifactId": artifact.artifact_id}, span.span_id))
        except Exception as exc:
            span.error = str(redact(str(exc)[:500]))
            span.latency_ms = (time.perf_counter() - started) * 1000
            with suppress(Exception):
                await self.control_plane.store_span(span)
            with suppress(Exception):
                await self._event(
                    "plan_node_failed", task, run_id,
                    {"nodeId": node.node_id, "error": span.error}, span.span_id,
                )
            raise
        span.latency_ms = (time.perf_counter() - started) * 1000
        await self.control_plane.store_span(span)
        events.append(await self._event("plan_node_completed", task, run_id,
                                        {"nodeId": node.node_id, "latencyMs": span.latency_ms}, span.span_id))
        return artifact, span, events

    async def execute(
        self,
        task: NormalizedTask,
        plan: Plan,
        lease_id: str,
        *,
        run_id: str | None = None,
        deadline: float | None = None,
    ) -> ExecutionResult:
        run_id = run_id or new_id("run")
        artifacts: dict[str, Artifact] = {}
        run_started = time.perf_counter()
        deadline = deadline or run_started + task.consent.max_runtime_s
        total_cost = 0.0
        events: list[CanonicalEvent] = []
        graph_payload = plan.model_dump(mode="json", by_alias=True)
        graph_payload.pop("planId", None)
        plan_identity = {
            "planId": plan.plan_id,
            "taskId": plan.task_id,
            "policyVersion": plan.policy_version,
            "graphHash": hashlib.sha256(
                json.dumps(graph_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
        try:
            events.append(await self._event("run_started", task, run_id, {"planId": plan.plan_id}))
            completed: set[str] = set()
            if self.cache and run_id:
                state = self.cache.load(run_id)
                if state:
                    cached_identity = state.get("planIdentity", {})
                    if any(
                        cached_identity.get(key) != plan_identity[key]
                        for key in ("taskId", "policyVersion", "graphHash")
                    ):
                        raise ValueError("resume cache belongs to a different plan graph")
                    for node_id, artifact_id in state.get("artifacts", {}).items():
                        artifacts[node_id] = self.artifact_store.get(artifact_id)
                    completed = set(state.get("completedNodes", [])) & set(artifacts)
            revisions = RevisionState()
            nodes = {node.node_id: node for node in plan.nodes}
            execution_services = self.execution_services or ExecutionServices(task, self.artifact_store.root.parent)
            if execution_services.task.task_id != task.task_id:
                raise ValueError("execution services are bound to a different task")
            # A resumed patch is evidence, not workspace state. Reapply exact,
            # already validated file artifacts before any downstream tool runs.
            for layer in execution_layers(plan):
                for node_id in layer:
                    if node_id not in completed:
                        continue
                    node = nodes[node_id]
                    if ArtifactType(node.output_artifact) not in {ArtifactType.PATCH, ArtifactType.PACKAGE_RESULT}:
                        continue
                    node_execution = execution_services.for_node(node)
                    node_execution.validate_output_scope(artifacts[node_id].content)
                    await node_execution.commit_validated_output(artifacts[node_id].content)
        except Exception as exc:
            await self._record_failure(events, task, run_id, lease_id, exc)
            raise
        try:
            for layer in execution_layers(plan):
                runnable = [node_id for node_id in layer if node_id not in completed]
                tasks = [
                    asyncio.create_task(
                        self._run_node(
                            task, run_id, nodes[node_id], artifacts, [], execution_services, deadline,
                        ),
                        name=f"helios-node-{run_id}-{node_id}",
                    )
                    for node_id in runnable
                ]
                try:
                    results = await asyncio.gather(*tasks)
                except Exception:
                    for node_task in tasks:
                        if not node_task.done():
                            node_task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise
                for node_id, (artifact, _, node_events) in zip(runnable, results, strict=True):
                    artifacts[node_id] = artifact
                    completed.add(node_id)
                    events.extend(node_events)
                total_cost += sum(span.cost_usd for _, span, _ in results)
                save_progress(
                    self.cache,
                    run_id,
                    completed,
                    {key: value.artifact_id for key, value in artifacts.items()},
                    plan_identity,
                )

                for node_id in runnable:
                    node = nodes[node_id]
                    artifact = artifacts[node_id]
                    if node.kind == NodeKind.CRITIC and artifact.content.get("verdict") == "revise":
                        notes = list(artifact.content.get("notes", []))
                        if revisions.permit(notes):
                            revision_targets = [
                                target
                                for revision_layer in execution_layers(plan)
                                for target in revision_layer
                                if target in node.dependencies
                            ]
                            for dependency in revision_targets:
                                replacement, replacement_span, extra = await self._run_node(
                                    task, run_id, nodes[dependency], artifacts, notes, execution_services, deadline,
                                )
                                artifacts[dependency] = replacement
                                total_cost += replacement_span.cost_usd
                                events.extend(extra)
                            replacement, replacement_span, extra = await self._run_node(
                                task, run_id, node, artifacts, notes, execution_services, deadline,
                            )
                            artifacts[node_id] = replacement
                            total_cost += replacement_span.cost_usd
                            events.extend(extra)
                            save_progress(
                                self.cache,
                                run_id,
                                completed,
                                {key: value.artifact_id for key, value in artifacts.items()},
                                plan_identity,
                            )
                        if artifacts[node_id].content.get("verdict") != "pass":
                            await self._store_escalation(
                                task, run_id, artifacts, notes, "one critic-directed revision",
                            )
                    elif node.kind == NodeKind.CRITIC and artifact.content.get("verdict") == "blocked":
                        await self._store_escalation(
                            task,
                            run_id,
                            artifacts,
                            list(artifact.content.get("notes", [])),
                            "critic identified a blocking decision",
                        )

            intent = artifacts.get(plan.terminal_node_id)
            status = "escalated"
            if intent and intent.content.get("authorized"):
                if self.writeback_enabled:
                    action = str(intent.content.get("action", ""))
                    if self.writeback_mode == "pr-only" and action not in {
                        "branch_pr",
                        "private_security_pr",
                    }:
                        events.append(await self._event(
                            "writeback_skipped",
                            task,
                            run_id,
                            {
                                "reason": "remote control permits pull requests only",
                                "intentId": intent.artifact_id,
                                "action": action,
                            },
                        ))
                    else:
                        if not await self.control_plane.lease_valid(lease_id):
                            raise LeaseLost("lease lost before write-back")
                        await self.control_plane.submit_intent(lease_id, intent)
                        status = "escalated" if action == "private_security_report" else "completed"
                else:
                    status = "dry_run"
                    events.append(await self._event(
                        "writeback_skipped",
                        task,
                        run_id,
                        {"reason": "write-back disabled", "intentId": intent.artifact_id,
                         "action": intent.content.get("action")},
                    ))
            latency_ms = (time.perf_counter() - run_started) * 1000
            events.append(await self._event("run_finished", task, run_id, {"status": status}))
            if status == "escalated":
                escalation_artifacts = [
                    artifact.artifact_id
                    for artifact in artifacts.values()
                    if artifact.artifact_type in {
                        ArtifactType.ESCALATION,
                        ArtifactType.SECURITY_REPORT,
                        ArtifactType.WRITEBACK_INTENT,
                    }
                ]
                action = str(intent.content.get("action", "")) if intent else ""
                await self.control_plane.escalate_task(
                    lease_id,
                    reason=(
                        "private security report requires restricted operator review"
                        if action == "private_security_report"
                        else "critic or policy requires operator review"
                    ),
                    run_id=run_id,
                    artifact_ids=escalation_artifacts,
                    restricted=action == "private_security_report",
                )
            else:
                await self.control_plane.finish_run(run_id, {
                    "status": status,
                    "intentId": intent.artifact_id if intent else None,
                    "latencyMs": latency_ms,
                    "actualCostUsd": total_cost,
                })
            return ExecutionResult(run_id=run_id, status=status, artifacts=artifacts, intent=intent,
                                   events=events, latency_ms=latency_ms, actual_cost_usd=total_cost)
        except Exception as exc:
            await self._record_failure(events, task, run_id, lease_id, exc)
            raise
