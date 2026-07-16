import json
from pathlib import Path

import httpx

from helios.config import Settings
from helios.control_plane import InMemoryControlPlane, RuntimeControlState
from helios.control_plane.convex_http import ConvexHttpControlPlane
from helios.control_plane.outbox import IdempotentOutbox
from helios.runtime import HeliosRuntime


CATALOG_PATH = Path(__file__).resolve().parents[1] / "agents" / "baseline.yaml"


def _settings(tmp_path: Path, *, writeback_mode: str = "dry-run") -> Settings:
    workspace = tmp_path / "workspace"
    return Settings(
        environment="test",
        control_plane_url="",
        worker_url="",
        convex_http_url="",
        helios_workspace_root=workspace,
        helios_outbox_path=workspace / "outbox.jsonl",
        git_repo_cache_root=workspace / "repos",
        helios_agent_catalog=CATALOG_PATH,
        helios_writeback_mode=writeback_mode,
    )


def test_runtime_control_state_accepts_member2_camel_case_and_has_safe_defaults():
    defaults = RuntimeControlState()

    assert defaults.global_paused is False
    assert defaults.emergency_mode is False
    assert defaults.paused_agents == []
    assert defaults.writeback_mode == "dry-run"
    assert defaults.security_scan_mode == "read-only"

    state = RuntimeControlState.model_validate({
        "globalPaused": True,
        "emergencyMode": True,
        "pausedAgents": ["backend", "javascript-slm"],
        "writebackMode": "pr-only",
        "securityScanMode": "remediation-approved",
        "currentAgentTag": "agents-v9",
        "currentAdapterPointers": {"html": "adapter-v2"},
        "updatedAt": 1_783_857_600_000,
        "futureMember2Field": "ignored for forward compatibility",
    })

    assert state.global_paused is True
    assert state.emergency_mode is True
    assert state.paused_agents == ["backend", "javascript-slm"]
    assert state.writeback_mode == "pr-only"
    assert state.security_scan_mode == "remediation-approved"
    assert state.current_agent_tag == "agents-v9"
    assert state.current_adapter_pointers == {"html": "adapter-v2"}
    assert state.updated_at == 1_783_857_600_000
    assert state.model_dump(mode="json", by_alias=True)["globalPaused"] is True


async def test_in_memory_global_pause_does_not_claim_queued_work(tmp_path, maintain_task):
    control = InMemoryControlPlane()
    control.control_state = RuntimeControlState(
        globalPaused=True,
        writebackMode="live",
    )
    await control.enqueue(maintain_task)
    runtime = HeliosRuntime(_settings(tmp_path, writeback_mode="intent"), control)

    assert await runtime.process_once() is False
    assert control.tasks.qsize() == 1
    assert control.leases == {}
    assert control.events == {}
    assert control.intents == {}
    assert runtime.state()["remoteControl"]["globalPaused"] is True


async def test_remote_dry_run_blocks_intent_even_when_local_writeback_is_enabled(
    tmp_path,
    maintain_task,
):
    control = InMemoryControlPlane()
    control.control_state = RuntimeControlState(writebackMode="dry-run")
    await control.enqueue(maintain_task)
    runtime = HeliosRuntime(_settings(tmp_path, writeback_mode="intent"), control)

    assert await runtime.process_once() is True

    assert control.intents == {}
    assert len(control.results) == 1
    result = next(iter(control.results.values()))
    assert result["status"] == "dry_run"
    skipped = [event for event in control.events.values() if event.type == "writeback_skipped"]
    assert len(skipped) == 1
    assert skipped[0].payload["reason"] == "write-back disabled"
    assert skipped[0].payload["intentId"] in control.artifacts
    assert runtime.state()["writebackMode"] == "dry-run"


async def test_convex_adapter_reads_controls_and_sends_lease_bound_escalation(maintain_task):
    calls: list[tuple[str, str, dict | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, payload))
        assert request.headers["Authorization"] == "Bearer runtime-test-token"
        if request.url.path == "/runtime/control":
            return httpx.Response(200, json={
                "globalPaused": False,
                "emergencyMode": False,
                "pausedAgents": ["security"],
                "writebackMode": "pr-only",
                "securityScanMode": "read-only",
                "currentAgentTag": "agents-v3",
                "currentAdapterPointers": {"css": "css-v4"},
                "updatedAt": 1_783_857_600_000,
            })
        if request.url.path == "/runtime/claim":
            return httpx.Response(200, json={
                "task": maintain_task.model_dump(mode="json", by_alias=True),
                "leaseId": "lease-control-test",
                "leaseToken": "lease-token-that-is-at-least-thirty-two-characters",
                "expiresAt": "2026-07-12T12:00:00Z",
            })
        if request.url.path == "/runtime/task/escalate":
            return httpx.Response(202, json={"ok": True})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    control = ConvexHttpControlPlane(
        "https://worker.example",
        "runtime-test-token",
        transport=httpx.MockTransport(handler),
    )
    try:
        state = await control.get_control_state()
        lease = await control.claim("runtime-1")
        assert lease is not None
        await control.escalate_task(
            lease.lease_id,
            reason="operator decision required",
            run_id="run-control-test",
            artifact_ids=["art-control-test"],
            restricted=True,
        )
    finally:
        await control.close()

    assert state.paused_agents == ["security"]
    assert state.writeback_mode == "pr-only"
    assert state.current_adapter_pointers == {"css": "css-v4"}
    assert [(method, path) for method, path, _ in calls] == [
        ("GET", "/runtime/control"),
        ("POST", "/runtime/claim"),
        ("POST", "/runtime/task/escalate"),
    ]
    escalation = calls[-1][2]
    assert escalation == {
        "taskId": maintain_task.task_id,
        "ownerId": "runtime-1",
        "leaseToken": "lease-token-that-is-at-least-thirty-two-characters",
        "runId": "run-control-test",
        "artifactIds": ["art-control-test"],
        "reason": "operator decision required",
        "restricted": True,
        "resultUrls": [],
        "error": {
            "code": "RUNTIME_ESCALATED",
            "message": "operator decision required",
            "retryable": False,
        },
    }


async def test_outbox_quarantines_malformed_lines_without_blocking_valid_records(tmp_path):
    path = tmp_path / "outbox.jsonl"
    path.write_text(
        "not-json\n"
        '{"id":"valid","kind":"event","payload":{"value":1}}\n'
        '{"id":7,"kind":"event","payload":{}}\n',
        encoding="utf-8",
    )
    outbox = IdempotentOutbox(path)
    delivered: list[dict] = []

    async def send(record: dict) -> None:
        delivered.append(record)

    assert await outbox.replay(send) == 1
    assert [record["id"] for record in delivered] == ["valid"]
    assert path.read_text(encoding="utf-8") == ""

    quarantined = [
        json.loads(line)
        for line in outbox.dead_letter_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["line"] for record in quarantined] == [1, 3]
    assert quarantined[0]["raw"] == "not-json"
    assert "string id" in quarantined[1]["error"]
