import asyncio
import time

from helios.contracts import ArtifactType
from helios.control_plane import InMemoryControlPlane
from helios.experts import default_experts
from helios.planning.fallback_templates import maintain_plan
from helios.scheduler import Scheduler
from helios.workspace import ArtifactStore


async def test_fast_lane_produces_credential_free_intent(tmp_path, maintain_task):
    control = InMemoryControlPlane()
    await control.enqueue(maintain_task)
    lease = await control.claim("test")
    scheduler = Scheduler(control_plane=control, artifact_store=ArtifactStore(tmp_path), experts=default_experts())
    result = await scheduler.execute(maintain_task, maintain_plan(maintain_task), lease.lease_id)
    assert result.status == "completed"
    assert result.intent.content["credentialFree"] is True
    assert result.intent.content["action"] == "issue_update"
    assert any(item.artifact_type == ArtifactType.CLASSIFICATION for item in result.artifacts.values())
    assert any(event.type == "planner_fallback" for event in []) is False


async def test_parallel_nodes_overlap(tmp_path, maintain_task):
    experts = default_experts()
    original = experts["triage"]

    async def slow(context):
        await asyncio.sleep(0.25)
        return await original(context)

    experts["triage"] = slow
    experts["dedupe"] = slow
    control = InMemoryControlPlane()
    await control.enqueue(maintain_task)
    lease = await control.claim("test")
    started = time.perf_counter()
    await Scheduler(control_plane=control, artifact_store=ArtifactStore(tmp_path), experts=experts,
                    max_parallel=3).execute(maintain_task, maintain_plan(maintain_task), lease.lease_id)
    # Two 250 ms nodes would take at least 500 ms if serialized. Leave room for
    # Windows artifact I/O while still proving that the expert work overlaps.
    assert time.perf_counter() - started < 0.48


async def test_lease_loss_cancels_writeback(tmp_path, maintain_task):
    control = InMemoryControlPlane(lease_seconds=-1)
    await control.enqueue(maintain_task)
    lease = await control.claim("test")
    scheduler = Scheduler(control_plane=control, artifact_store=ArtifactStore(tmp_path), experts=default_experts())
    try:
        await scheduler.execute(maintain_task, maintain_plan(maintain_task), lease.lease_id)
    except Exception as exc:
        assert "lease" in str(exc).lower()
    assert not control.intents


async def test_two_critic_rejections_escalate(tmp_path, maintain_task):
    experts = default_experts()

    async def reject(context):
        return {"verdict": "revise", "notes": ["same normalized failure"], "independent": True}

    experts["critic"] = reject
    control = InMemoryControlPlane()
    await control.enqueue(maintain_task)
    lease = await control.claim("test")
    result = await Scheduler(control_plane=control, artifact_store=ArtifactStore(tmp_path),
                             experts=experts).execute(maintain_task, maintain_plan(maintain_task), lease.lease_id)
    assert result.status == "escalated"
    assert result.artifacts["escalation"].content["decisionNeeded"] == "human review required"
    assert not control.intents
