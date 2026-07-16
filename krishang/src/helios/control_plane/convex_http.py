import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from helios.clock import now_utc
from helios.contracts import Artifact, ArtifactType, CanonicalEvent, NormalizedTask, Span
from helios.ids import new_id
from helios.security.redaction import redact_text

from .base import ControlPlane, Lease, LeaseLost, RuntimeControlState
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
        self._run_start_lock = asyncio.Lock()

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        for attempt in range(3):
            response = await self.client.request(method, path, json=json)
            if response.status_code in (401, 403, 422):
                response.raise_for_status()
            if response.status_code == 409:
                if path in {"/runtime/heartbeat", "/runtime/run/finish", "/runtime/task/escalate", "/runtime/writeback"}:
                    raise LeaseLost("control plane reports a lost lease")
                detail = response.text[:500]
                raise RuntimeError(f"control-plane conflict for {path}: {detail}")
            if response.status_code != 429 and response.status_code < 500:
                response.raise_for_status()
                return response.json() if response.content else None
            if attempt == 2:
                response.raise_for_status()
            await asyncio.sleep(0.25 * (2**attempt))
        raise RuntimeError("unreachable control-plane retry state")

    async def get_control_state(self) -> RuntimeControlState:
        value = await self._request("GET", "/runtime/control")
        return RuntimeControlState.model_validate(value or {})

    async def get_agent_config(self) -> dict[str, Any]:
        value = await self._request("GET", "/runtime/config/agents")
        if not isinstance(value, dict) or not isinstance(value.get("agents"), list):
            raise ValueError("control plane returned an invalid agent registry")
        adapters = value.get("adapters", {})
        if not isinstance(adapters, dict):
            raise ValueError("control plane returned invalid adapter pointers")
        return {"agents": value["agents"], "adapters": adapters}

    async def resume_sequence(self, run_id: str) -> int:
        value = await self._request("GET", f"/runtime/run/resume?runId={quote(run_id, safe='')}")
        next_sequence = int(value.get("nextSequence", 0)) if isinstance(value, dict) else 0
        if next_sequence < 1:
            raise ValueError("control plane returned an invalid resume sequence")
        task_id = str(value.get("taskId", ""))
        lease_id = next(
            (key for key, state in self._leases.items() if state["taskId"] == task_id),
            None,
        )
        if not lease_id:
            raise LeaseLost("resumed run is not associated with the claimed task")
        self._run_leases[run_id] = lease_id
        self._started_runs.add(run_id)
        return next_sequence - 1

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
        stale_lease_ids = [
            key for key, state in self._leases.items() if state["taskId"] == task.task_id
        ]
        for stale_lease_id in stale_lease_ids:
            self._leases.pop(stale_lease_id, None)
        for stale_run_id, run_lease_id in list(self._run_leases.items()):
            if run_lease_id in stale_lease_ids:
                self._run_leases.pop(stale_run_id, None)
                self._started_runs.discard(stale_run_id)
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
        payload = artifact.model_dump(mode="json", by_alias=True)
        payload["content"] = json.dumps(
            artifact.content,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        await self._durable_post(
            "/runtime/artifact",
            artifact.artifact_id,
            payload,
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
        self._run_leases.pop(run_id, None)
        self._started_runs.discard(run_id)
        self._leases.pop(lease_id, None)

    async def submit_intent(self, lease_id: str, intent: Artifact) -> None:
        state = self._lease(lease_id)
        task = self._tasks[state["taskId"]]
        critic = self._critic_for_intent(intent)
        action = str(intent.content.get("action", ""))
        reviewed_artifacts = self._reviewed_artifacts(critic)
        reviewed = self._select_reviewed_artifact(reviewed_artifacts, action)
        if action == "private_security_report":
            await self._store_private_security_report(task, intent, reviewed_artifacts, state)
            return
        if action in {"issue_update", "review_comment"}:
            external_action = "comment"
            payload = {"action": external_action, "data": _comment_payload(action, intent, task, reviewed)}
        elif action == "labels_set":
            issue_number = intent.content.get("issueNumber") or task.metadata.get("issueNumber")
            labels = intent.content.get("labels") or reviewed.content.get("labels")
            if not isinstance(issue_number, int) or issue_number <= 0 or not isinstance(labels, list) or not labels:
                raise ValueError("label write-back requires an issue number and critic-approved labels")
            normalized_labels = [str(item).strip()[:256] for item in labels if str(item).strip()]
            if not normalized_labels:
                raise ValueError("label write-back has no valid critic-approved labels")
            external_action = "labels_set"
            payload = {
                "action": external_action,
                "data": {"issueNumber": issue_number, "labels": normalized_labels[:20]},
            }
        elif action == "milestone_set":
            issue_number = intent.content.get("issueNumber") or task.metadata.get("issueNumber")
            milestone = intent.content.get("milestoneNumber") or task.metadata.get("milestoneNumber")
            if not isinstance(issue_number, int) or issue_number <= 0 or not isinstance(milestone, int) or milestone <= 0:
                raise ValueError("milestone write-back requires positive issue and milestone numbers")
            external_action = "milestone_set"
            payload = {"action": external_action, "data": {"issueNumber": issue_number, "milestoneNumber": milestone}}
        elif action == "duplicate_close":
            issue_number = intent.content.get("issueNumber") or task.metadata.get("issueNumber")
            duplicate_of = intent.content.get("duplicateOf") or task.metadata.get("duplicateOf")
            confidence = float(reviewed.content.get("confidence", 0))
            if (
                not reviewed.content.get("isExactDuplicate")
                or confidence < 0.92
                or not isinstance(issue_number, int)
                or issue_number <= 0
                or not isinstance(duplicate_of, int)
                or duplicate_of <= 0
                or duplicate_of == issue_number
            ):
                raise ValueError("duplicate close requires exact critic-approved duplicate evidence")
            external_action = "duplicate_close"
            payload = {"action": external_action, "data": {
                "issueNumber": issue_number,
                "duplicateOf": duplicate_of,
                "comment": str(intent.content.get("comment") or "Closing as an exact duplicate.")[:128_000],
                "confidence": confidence,
            }}
        elif action in {"branch_pr", "private_security_pr"}:
            files = reviewed.content.get("files")
            if not isinstance(files, list) or not files:
                raise ValueError("branch write-back requires at least one critic-approved file")
            normalized_files = [
                {"path": str(item["path"]), "content": str(item["content"]), "encoding": "utf-8"}
                for item in files if isinstance(item, dict) and item.get("path") and "content" in item
            ]
            if not normalized_files:
                raise ValueError("branch write-back has no valid critic-approved files")
            external_action = (
                "security_pr"
                if action == "private_security_pr"
                else "build_branch_and_pr"
                if task.mode.value == "build"
                else "branch_and_pr"
            )
            branch_suffix = task.task_id.split("_", 1)[-1].lower()[:20]
            payload = {
                "action": external_action,
                "data": {
                    "branch": f"hermes/task-{branch_suffix}",
                    "title": task.title[:256],
                    "body": f"Automated draft for task `{task.task_id}`.\n\n{task.body}"[:128_000],
                    "files": normalized_files,
                    "draft": True,
                },
            }
        elif action == "draft_release":
            external_action = "release_draft"
            payload = {"action": external_action, "data": {
                "tagName": str(intent.content.get("tagName") or task.metadata.get("tagName") or "next")[:256],
                "name": str(intent.content.get("name") or task.title)[:256],
                "body": str(reviewed.content.get("notes") or task.body or task.title)[:128_000],
                "targetCommitish": str(task.metadata.get("targetCommitish") or "main")[:256],
                "draft": True,
            }}
        else:
            raise ValueError(f"connector action {action!r} is not implemented")
        requires_quality_gates = action in {"branch_pr", "private_security_pr"}
        tests_passed = not requires_quality_gates or self._reviewed_tests_passed(reviewed_artifacts)
        security_passed = not requires_quality_gates or self._reviewed_security_passed(reviewed_artifacts)
        writeback = {
            "schemaVersion": 1,
            "writebackId": new_id("writeback"),
            "taskId": task.task_id,
            "runId": intent.run_id,
            "repo": task.repository,
            "action": external_action,
            "idempotencyKey": str(intent.content.get("idempotencyKey") or f"{task.task_id}:comment"),
            "leaseToken": state["token"],
            "artifactId": reviewed.artifact_id,
            "artifactHash": reviewed.content_hash,
            "criticArtifactId": critic.artifact_id,
            "policyRuleIds": intent.policy_ids or ["runtime.credential-free"],
            "requiredChecksPassed": tests_passed,
            "securityChecksPassed": security_passed,
            "testsPassed": tests_passed,
            "breakingChange": False,
            "requestedAt": _epoch_ms(),
            "payload": payload,
            **({"baseSha": task.base_sha} if task.base_sha and set(task.base_sha) != {"0"} else {}),
        }
        value = await self._request("POST", "/runtime/writeback", {
            "intent": writeback,
            "leaseToken": state["token"],
        })
        result_url = value.get("resultUrl") if isinstance(value, dict) else None
        if not isinstance(result_url, str) or not result_url.startswith("https://"):
            raise ValueError("write-back did not return a persisted HTTPS result URL")
        self._result_urls.setdefault(intent.run_id, []).append(result_url)

    def _reviewed_artifacts(self, critic: Artifact) -> list[Artifact]:
        records = critic.content.get("reviewedArtifacts")
        if not isinstance(records, list):
            records = [{
                "artifactId": critic.content.get("reviewedArtifactId"),
                "contentHash": critic.content.get("reviewedContentHash"),
            }]
        reviewed: list[Artifact] = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("critic lineage record is invalid")
            artifact_id = str(record.get("artifactId") or record.get("reviewedArtifactId") or "")
            expected_hash = record.get("contentHash") or record.get("reviewedContentHash")
            artifact = self._artifacts.get(artifact_id)
            if not artifact or expected_hash != artifact.content_hash:
                raise ValueError("critic did not review a known exact artifact")
            reviewed.append(artifact)
        if not reviewed:
            raise ValueError("critic reviewed no artifacts")
        return reviewed

    @staticmethod
    def _select_reviewed_artifact(reviewed: list[Artifact], action: str) -> Artifact:
        if action in {"branch_pr", "private_security_pr"}:
            return next((item for item in reviewed if item.content.get("files")), reviewed[0])
        if action == "draft_release":
            return next((item for item in reviewed if item.artifact_type == ArtifactType.RELEASE_DRAFT), reviewed[0])
        if action == "duplicate_close":
            return next((item for item in reviewed if item.artifact_type == ArtifactType.DUP_REPORT), reviewed[0])
        if action in {"issue_update", "review_comment"}:
            return next((item for item in reviewed if item.content.get("body") or item.content.get("summary")), reviewed[0])
        return reviewed[0]

    async def _store_private_security_report(
        self,
        task: NormalizedTask,
        intent: Artifact,
        reviewed: list[Artifact],
        lease_state: dict[str, Any],
    ) -> None:
        report = next((item for item in reviewed if item.artifact_type == ArtifactType.SECURITY_REPORT), reviewed[0])
        findings = report.content.get("findings", [])
        if not isinstance(findings, list):
            raise ValueError("security report findings must be a list")
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            kind = str(finding.get("kind") or "sast").lower()
            category = {
                "config": "configuration",
                "configuration": "configuration",
                "dependency": "dependency",
                "sast": "sast",
                "secret": "secret",
                "supply_chain": "supply_chain",
            }.get(kind, "sast")
            severity = str(finding.get("severity") or "info").lower()
            severity = {"warning": "medium", "error": "high", "unknown": "info"}.get(severity, severity)
            if severity not in {"info", "low", "medium", "high", "critical"}:
                severity = "info"
            confidence = str(finding.get("confidence") or "low").lower()
            if confidence not in {"low", "medium", "high", "confirmed"}:
                confidence = "low"
            exploitability = str(finding.get("exploitability") or "none").lower()
            if exploitability not in {"none", "theoretical", "conditional", "likely", "demonstrated_safe_fixture"}:
                exploitability = "none"
            reachability = str(finding.get("reachability") or "unknown").lower()
            if reachability not in {"unknown", "unreachable", "potentially_reachable", "reachable"}:
                reachability = "unknown"
            fingerprint = str(finding.get("fingerprint") or report.content_hash)
            finding_payload = {
                "findingId": str(finding.get("findingId") or new_id("fnd")),
                "taskId": task.task_id,
                "repo": task.repository,
                "commitSha": task.base_sha,
                "scanner": str(finding.get("scanner") or "helios-local")[:256],
                "scannerVersion": str(finding.get("scannerVersion") or "unknown")[:256],
                "ruleId": str(finding.get("ruleId") or "helios.unknown")[:256],
                "fingerprint": fingerprint,
                "evidenceFingerprint": fingerprint,
                "severity": severity,
                "confidence": confidence,
                "category": category,
                "exploitability": exploitability,
                "reachability": reachability,
                "path": str(finding.get("path") or "unknown")[:512],
                "startLine": finding.get("line"),
                "evidenceRedacted": redact_text(str(finding.get("evidence") or "Evidence withheld"))[:8_192],
                "recommendedFix": redact_text(str(finding.get("remediation") or "Review and remediate the finding"))[:8_192],
                "advisoryUrls": finding.get("advisoryUrls") if isinstance(finding.get("advisoryUrls"), list) else [],
                "status": str(finding.get("status") or "open"),
                "artifactIds": [report.artifact_id, intent.artifact_id],
                "findingIndex": index,
                "restricted": True,
            }
            await self._request("POST", "/runtime/security/findings", {
                "taskId": task.task_id,
                "ownerId": lease_state["ownerId"],
                "leaseToken": lease_state["token"],
                "finding": finding_payload,
            })

    async def escalate_task(
        self,
        lease_id: str,
        *,
        reason: str,
        run_id: str | None = None,
        artifact_ids: list[str] | None = None,
        restricted: bool = False,
    ) -> None:
        state = self._lease(lease_id)
        await self._request("POST", "/runtime/task/escalate", {
            "taskId": state["taskId"],
            "ownerId": state["ownerId"],
            "leaseToken": state["token"],
            "runId": run_id,
            "artifactIds": list(artifact_ids or []),
            "reason": reason[:500],
            "restricted": restricted,
            "resultUrls": [],
            "error": {"code": "RUNTIME_ESCALATED", "message": reason[:500], "retryable": False},
        })
        self._leases.pop(lease_id, None)
        if run_id:
            self._run_leases.pop(run_id, None)
            self._started_runs.discard(run_id)

    @staticmethod
    def _quality_gate(artifact: Artifact, key: str, *, allow_empty: bool = False) -> bool:
        records = artifact.content.get(key, [])
        if not isinstance(records, list) or (not records and not allow_empty):
            return False
        for record in records:
            if not isinstance(record, dict):
                return False
            if key == "testResults" and record.get("success") is not True:
                return False
            if key == "securityResults" and record.get("safe") is not True:
                return False
        return True

    @classmethod
    def _reviewed_tests_passed(cls, reviewed: list[Artifact]) -> bool:
        manifests = [item for item in reviewed if "testResults" in item.content]
        if manifests:
            return any(cls._quality_gate(item, "testResults") for item in manifests)
        return any(
            item.artifact_type == ArtifactType.TEST_RESULT
            and item.content.get("authoritative") is True
            and item.content.get("fabricated") is False
            and item.content.get("success") is True
            for item in reviewed
        )

    @classmethod
    def _reviewed_security_passed(cls, reviewed: list[Artifact]) -> bool:
        manifests = [item for item in reviewed if "securityResults" in item.content]
        if manifests:
            return any(cls._quality_gate(item, "securityResults") for item in manifests)
        return any(
            (
                item.artifact_type == ArtifactType.SECURITY_REPORT
                and item.content.get("authoritative") is True
                and item.content.get("safe") is True
                and item.content.get("coverageComplete") is True
            )
            or (
                item.artifact_type == ArtifactType.SARIF_REPORT
                and item.content.get("authoritative") is True
                and item.content.get("coverageComplete") is True
                and not item.content.get("findings")
            )
            for item in reviewed
        )

    async def _ensure_run(self, task_id: str, run_id: str, started_at: datetime) -> None:
        async with self._run_start_lock:
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
                "leaseToken": self._lease(lease_id)["token"],
            })
            self._run_leases[run_id] = lease_id
            self._started_runs.add(run_id)

    async def close(self) -> None:
        await self.client.aclose()

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
