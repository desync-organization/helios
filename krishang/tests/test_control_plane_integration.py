import re
from datetime import UTC, datetime

import httpx

from helios.config import Settings
from helios.contracts import Artifact, ArtifactType, CanonicalEvent
from helios.control_plane import InMemoryControlPlane
from helios.control_plane.convex_http import ConvexHttpControlPlane, _comment_payload
from helios.ids import new_id
from helios.runtime import HeliosRuntime


def test_runtime_defaults_to_in_memory_control_plane(tmp_path):
    runtime = HeliosRuntime(Settings(
        helios_workspace_root=tmp_path / "workspace",
        git_repo_cache_root=tmp_path / "repos",
        helios_outbox_path=tmp_path / "outbox.jsonl",
    ))
    assert isinstance(runtime.control_plane, InMemoryControlPlane)


def test_generated_ids_match_control_plane_contracts():
    patterns = {
        "task": r"^tsk_[0-9A-HJKMNP-TV-Z]{26}$",
        "run": r"^run_[0-9A-HJKMNP-TV-Z]{26}$",
        "span": r"^spn_[0-9A-HJKMNP-TV-Z]{26}$",
        "artifact": r"^art_[0-9A-HJKMNP-TV-Z]{26}$",
        "event": r"^evt_[0-9A-HJKMNP-TV-Z]{26}$",
        "writeback": r"^wba_[0-9A-HJKMNP-TV-Z]{26}$",
    }
    for kind, pattern in patterns.items():
        assert re.fullmatch(pattern, new_id(kind))


def test_pr_review_intent_becomes_a_critic_approved_pr_comment(maintain_task):
    task = maintain_task.model_copy(update={"metadata": {"pullNumber": 42}})
    review = Artifact.create(
        task_id=task.task_id,
        run_id=new_id("run"),
        artifact_type=ArtifactType.REVIEW_NOTES,
        producer="backend",
        content={"summary": "Two gates passed.", "findings": ["Add a regression test."]},
    )
    intent = Artifact.create(
        task_id=task.task_id,
        run_id=review.run_id,
        artifact_type=ArtifactType.WRITEBACK_INTENT,
        producer="intent",
        content={"authorized": True, "action": "review_comment", "pullNumber": 42},
    )
    assert _comment_payload("review_comment", intent, task, review) == {
        "issueNumber": 42,
        "body": "## Hermes PR review\n\nTwo gates passed.\n\n### Findings\n- Add a regression test.",
    }


async def test_http_adapter_bridges_issue_reply_to_member2_writeback(maintain_task):
    task = maintain_task.model_copy(update={
        "task_id": new_id("task"),
        "metadata": {"issueNumber": 7},
    })
    calls: list[tuple[str, dict | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = None
        if request.content:
            payload = __import__("json").loads(request.content)
        calls.append((request.url.path, payload))
        if request.url.path == "/runtime/claim":
            return httpx.Response(200, json={
                "task": task.model_dump(mode="json", by_alias=True),
                "leaseId": "lse_test",
                "leaseToken": "lease-token-that-is-at-least-thirty-two-characters",
                "expiresAt": "2026-07-12T12:00:00Z",
            })
        if request.url.path == "/runtime/heartbeat":
            return httpx.Response(200, json={"ok": True, "expiresAt": 1_783_857_600_000})
        if request.url.path == "/runtime/writeback":
            return httpx.Response(200, json={
                "status": "completed",
                "resultUrl": "https://github.com/owner/repo/issues/7#issuecomment-1",
            })
        return httpx.Response(202, json={"ok": True})

    control = ConvexHttpControlPlane(
        "https://control.example",
        "runtime-token-that-is-at-least-thirty-two-characters",
        transport=httpx.MockTransport(handler),
    )
    lease = await control.claim("runtime-1")
    assert lease is not None
    run_id = new_id("run")
    await control.emit_event(CanonicalEvent(
        type="run_started",
        task_id=task.task_id,
        run_id=run_id,
        sequence=1,
        timestamp=datetime(2026, 7, 12, tzinfo=UTC),
    ))
    reply = Artifact.create(
        task_id=task.task_id,
        run_id=run_id,
        artifact_type=ArtifactType.DRAFT_REPLY,
        producer="docs",
        content={"body": "Verified response with repository evidence."},
    )
    critic = Artifact.create(
        task_id=task.task_id,
        run_id=run_id,
        artifact_type=ArtifactType.CRITIC_VERDICT,
        producer="critic",
        upstream_artifact_ids=[reply.artifact_id],
        content={
            "verdict": "pass",
            "reviewedArtifactId": reply.artifact_id,
            "reviewedContentHash": reply.content_hash,
            "producerAgent": "docs",
            "criticAgent": "critic",
        },
    )
    intent = Artifact.create(
        task_id=task.task_id,
        run_id=run_id,
        artifact_type=ArtifactType.WRITEBACK_INTENT,
        producer="intent",
        upstream_artifact_ids=[critic.artifact_id],
        policy_ids=["runtime.credential-free"],
        content={
            "authorized": True,
            "action": "issue_update",
            "issueNumber": 7,
            "idempotencyKey": f"{task.task_id}:comment",
        },
    )
    for artifact in (reply, critic, intent):
        await control.store_artifact(artifact)
    await control.submit_intent(lease.lease_id, intent)
    await control.finish_run(run_id, {"status": "completed", "latencyMs": 10, "actualCostUsd": 0})

    paths = [path for path, _ in calls]
    assert paths == [
        "/runtime/claim",
        "/runtime/run/start",
        "/runtime/event",
        "/runtime/artifact",
        "/runtime/artifact",
        "/runtime/artifact",
        "/runtime/writeback",
        "/runtime/run/finish",
    ]
    writeback = next(payload for path, payload in calls if path == "/runtime/writeback")
    assert writeback["intent"]["payload"] == {
        "action": "comment",
        "data": {"issueNumber": 7, "body": "Verified response with repository evidence."},
    }
    finish = next(payload for path, payload in calls if path == "/runtime/run/finish")
    assert finish["taskStatus"] == "done"
    assert finish["resultUrls"] == ["https://github.com/owner/repo/issues/7#issuecomment-1"]
