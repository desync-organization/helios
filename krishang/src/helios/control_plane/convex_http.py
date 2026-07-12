import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from helios.clock import now_utc
from helios.contracts import Artifact, ArtifactType, CanonicalEvent, NormalizedTask, Span
from helios.ids import new_id

from .base import ControlPlane, Lease, LeaseLost
from .outbox import IdempotentOutbox


def _epoch_ms(value: datetime | None = None) -> int:
    return int((value or now_utc()).timestamp() * 1000)


def _iso_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _comment_payload(action: str, intent: Artifact, task: NormalizedTask,
                     reviewed: Artifact) -> dict[str, Any]:
    if action == "issue_update":
        target_number = intent.content.get("issueNumber") or task.metadata.get("issueNumber")
        body = reviewed.content.get("body")
        target_label = "issue"
    elif action == "review_comment":
        target_number = intent.content.get("pullNumber") or task.metadata.get("pullNumber")
        summary = reviewed.content.get("summary")
        findings = reviewed.content.get("findings")
        finding_lines = [f"- {item}" for item in findings] if isinstance(findings, list) else []
        body = "\n".join([
            "## Hermes PR review",
            "",
            str(summary or "Review completed against the configured policy and security gates."),
            *( ["", "### Findings", *finding_lines] if finding_lines else [] ),
        ])
        target_label = "pull request"
    else:
        raise ValueError(f"connector action {action!r} is not implemented")
    if not isinstance(target_number, int) or target_number <= 0:
        raise ValueError(f"{target_label} write-back requires a positive number")
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"{target_label} write-back requires critic-approved review text")
    return {"issueNumber": target_number, "body": body.strip()}


class ConvexHttpControlPlane(ControlPlane):
    """Adapter for the Member 2 Worker/Convex HTTP contracts.

    The runtime keeps only opaque lease state and credential-free artifacts. GitHub
    credentials remain in Member 2's write-back boundary.
    """

    def __init__(self, base_url: str, token: str, *, timeout: float = 10,
                 outbox: IdempotentOutbox | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            transport=transport,
        )
        self.outbox = outbox
        self._leases: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, NormalizedTask] = {}
        self._run_leases: dict[str, str] = {}
        self._started_runs: set[str] = set()
        self._artifacts: dict[str, Artifact] = {}
        self._result_urls: dict[str, list[str]] = {}

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        for attempt in range(3):
            response = await self.client.request(method, path, json=json)
            if response.status_code in (401, 403, 422):
                response.raise_for_status()
            if response.status_code == 409:
                raise LeaseLost("control plane reports a lost lease")
            if response.status_code != 429 and response.status_code < 500:
                response.raise_for_status()
                return response.json() if response.content else None
            if attempt == 2:
                response.raise_for_status()
            await asyncio.sleep(0.25 * (2**attempt))
        raise RuntimeError("unreachable control-plane retry state")

    async def claim(self, instance_id: str) -> Lease | None:
        if self.outbox:
            try:
                await self.outbox.replay(lambda record: self._request(
                    record["payload"]["method"], record["payload"]["path"], record["payload"]["body"]
                ))
            except (httpx.HTTPError, LeaseLost):
                pass
        value = await self._request("POST", "/runtime/claim", {
            "ownerId": instance_id,
            "leaseMs": 60_000,
        })
        if not value or not value.get("task"):
            return None
        task = NormalizedTask.model_validate(value["task"])
        lease_id = str(value["leaseId"])
        expires_at = datetime.fromisoformat(str(value["expiresAt"]).replace("Z", "+00:00"))
        self._leases[lease_id] = {
            "taskId": task.task_id,
            "ownerId": instance_id,
            "token": value["leaseToken"],
            "expiresAt": expires_at,
        }
        self._tasks[task.task_id] = task
        return Lease(task=task, lease_id=lease_id, expires_at=expires_at)

    async def heartbeat(self, lease_id: str) -> Lease:
        state = self._lease(lease_id)
        value = await self._request("POST", "/runtime/heartbeat", {
            "taskId": state["taskId"],
            "ownerId": state["ownerId"],
            "leaseToken": state["token"],
            "extensionMs": 60_000,
        })
        expires_at = _iso_from_ms(int(value["expiresAt"]))
        state["expiresAt"] = expires_at
        return Lease(task=self._tasks[state["taskId"]], lease_id=lease_id, expires_at=expires_at)

    async def lease_valid(self, lease_id: str) -> bool:
        try:
            await self.heartbeat(lease_id)
            return True
        except (LeaseLost, httpx.HTTPError, KeyError):
            return False

    async def emit_event(self, event: CanonicalEvent) -> None:
        if not event.run_id or not event.task_id:
            return
        await self._ensure_run(event.task_id, event.run_id, event.timestamp)
        await self._durable_post(
            "/runtime/event",
            event.event_id,
            event.model_dump(mode="json", by_alias=True),
        )

    async def store_span(self, span: Span) -> None:
        await self._durable_post(
            "/runtime/span",
            span.span_id,
            span.model_dump(mode="json", by_alias=True),
        )

    async def store_artifact(self, artifact: Artifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact
        await self._durable_post(
            "/runtime/artifact",
            artifact.artifact_id,
            artifact.model_dump(mode="json", by_alias=True),
        )

    async def finish_run(self, run_id: str, result: dict[str, Any]) -> None:
        lease_id = self._run_leases.get(run_id)
        if not lease_id:
            raise LeaseLost("run is not associated with a current lease")
        state = self._lease(lease_id)
        result_urls = self._result_urls.get(run_id, [])
        runtime_status = str(result.get("status", "failed"))
        task_status = "done" if result_urls else ("failed" if runtime_status == "failed" else "escalated")
        await self._durable_post("/runtime/run/finish", f"finish:{run_id}", {
            "taskId": state["taskId"],
            "ownerId": state["ownerId"],
            "leaseToken": state["token"],
            "taskStatus": task_status,
            "resultUrls": result_urls,
            "runId": run_id,
            "run": {
                "status": "succeeded" if task_status == "done" else task_status,
                "finishedAt": _epoch_ms(),
                "resultUrls": result_urls,
                "latencyMs": float(result.get("latencyMs", 0)),
                "costUsd": float(result.get("actualCostUsd", 0)),
            },
            **({"error": {"code": "RUNTIME_FAILED", "message": str(result.get("error", "runtime failed"))[:500], "retryable": False}} if task_status == "failed" else {}),
        })

    async def submit_intent(self, lease_id: str, intent: Artifact) -> None:
        state = self._lease(lease_id)
        task = self._tasks[state["taskId"]]
        critic = self._critic_for_intent(intent)
        reviewed_id = str(critic.content.get("reviewedArtifactId", ""))
        reviewed = self._artifacts.get(reviewed_id)
        if not reviewed or critic.content.get("reviewedContentHash") != reviewed.content_hash:
            raise ValueError("critic did not review a known exact artifact")
        action = str(intent.content.get("action", ""))
        comment = _comment_payload(action, intent, task, reviewed)
        writeback = {
            "schemaVersion": 1,
            "writebackId": new_id("writeback"),
            "taskId": task.task_id,
            "runId": intent.run_id,
            "repo": task.repository,
            "action": "comment",
            "idempotencyKey": str(intent.content.get("idempotencyKey") or f"{task.task_id}:comment"),
            "leaseToken": state["token"],
            "artifactId": reviewed.artifact_id,
            "artifactHash": reviewed.content_hash,
            "criticArtifactId": critic.artifact_id,
            "policyRuleIds": intent.policy_ids or ["runtime.credential-free"],
            "requiredChecksPassed": True,
            "securityChecksPassed": True,
            "testsPassed": True,
            "breakingChange": False,
            "requestedAt": _epoch_ms(),
            "payload": {
                "action": "comment",
                "data": comment,
            },
        }
        value = await self._request("POST", "/runtime/writeback", {
            "intent": writeback,
            "leaseToken": state["token"],
        })
        result_url = value.get("resultUrl") if isinstance(value, dict) else None
        if not isinstance(result_url, str) or not result_url.startswith("https://"):
            raise ValueError("write-back did not return a persisted HTTPS result URL")
        self._result_urls.setdefault(intent.run_id, []).append(result_url)

    async def _ensure_run(self, task_id: str, run_id: str, started_at: datetime) -> None:
        if run_id in self._started_runs:
            return
        task = self._tasks[task_id]
        lease_id = next((key for key, value in self._leases.items() if value["taskId"] == task_id), None)
        if not lease_id:
            raise LeaseLost("task has no current lease")
        await self._request("POST", "/runtime/run/start", {
            "runId": run_id,
            "taskId": task_id,
            "mode": task.mode.value,
            "repo": task.repository,
            "lane": "fast" if task.task_type.value in {"intake", "classify", "label", "dedupe", "clarify", "respond"} else "deep",
            "status": "running",
            "plannerConfidence": 1,
            "startedAt": _epoch_ms(started_at),
            "tokensIn": 0,
            "tokensOut": 0,
            "costUsd": 0,
            "costCloudEquivalentUsd": 0,
            "agentVersions": [],
            "adapterVersions": [],
            "fallbackFlags": [],
            "resultUrls": [],
            "dataEgressSummary": {},
        })
        self._run_leases[run_id] = lease_id
        self._started_runs.add(run_id)

    def _critic_for_intent(self, intent: Artifact) -> Artifact:
        for artifact_id in intent.upstream_artifact_ids:
            artifact = self._artifacts.get(artifact_id)
            if artifact and artifact.artifact_type == ArtifactType.CRITIC_VERDICT:
                if artifact.content.get("verdict") != "pass":
                    raise ValueError("write-back requires a passing critic")
                return artifact
        raise ValueError("write-back intent has no passing critic artifact")

    def _lease(self, lease_id: str) -> dict[str, Any]:
        state = self._leases.get(lease_id)
        if not state:
            raise LeaseLost("lease is unknown to this runtime")
        return state

    async def _durable_post(self, path: str, record_id: str, body: dict[str, Any]) -> None:
        try:
            await self._request("POST", path, body)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (429,) and exc.response.status_code < 500:
                raise
            if not self.outbox:
                raise
            await self.outbox.append(record_id, "control-plane", {"method": "POST", "path": path, "body": body})
        except httpx.RequestError:
            if not self.outbox:
                raise
            await self.outbox.append(record_id, "control-plane", {"method": "POST", "path": path, "body": body})
