from helios.control_plane import InMemoryControlPlane
from helios.control_plane.local_cache import LocalRunCache
from helios.control_plane.outbox import IdempotentOutbox
from helios.experts import default_experts
from helios.planning.fallback_templates import maintain_plan
from helios.scheduler import Scheduler
from helios.workspace import ArtifactStore


async def test_outbox_replay_is_idempotent(tmp_path):
    outbox = IdempotentOutbox(tmp_path / "outbox.jsonl")
    await outbox.append("same", "event", {"value": 1})
    await outbox.append("same", "event", {"value": 1})
    delivered = []

    async def send(record):
        delivered.append(record)

    assert await outbox.replay(send) == 1
    assert len(delivered) == 1
    assert await outbox.replay(send) == 0


async def test_restart_hydrates_completed_artifacts_without_duplicate_spans(tmp_path, maintain_task):
    control = InMemoryControlPlane()
    await control.enqueue(maintain_task)
    lease = await control.claim("test")
    cache = LocalRunCache(tmp_path / "state")
    store = ArtifactStore(tmp_path / "artifacts")
    first = Scheduler(control_plane=control, artifact_store=store, experts=default_experts(), cache=cache)
    result = await first.execute(maintain_task, maintain_plan(maintain_task), lease.lease_id, run_id="run_resume")
    span_count = len(control.spans)
    await control.enqueue(maintain_task)
    next_lease = await control.claim("test")
    resumed = Scheduler(control_plane=control, artifact_store=store, experts=default_experts(), cache=cache)
    second = await resumed.execute(maintain_task, maintain_plan(maintain_task), next_lease.lease_id, run_id=result.run_id)
    assert second.intent.artifact_id == result.intent.artifact_id
    assert len(control.spans) == span_count


async def test_ten_warmed_fast_runs_record_latency_and_actual_cost(tmp_path, maintain_task):
    control = InMemoryControlPlane()
    results = []
    for index in range(10):
        task = maintain_task.model_copy(update={"task_id": f"task_warm_{index}"})
        await control.enqueue(task)
        lease = await control.claim("test")
        scheduler = Scheduler(control_plane=control,
                              artifact_store=ArtifactStore(tmp_path / str(index)),
                              experts=default_experts())
        results.append(await scheduler.execute(task, maintain_plan(task), lease.lease_id))
    assert len(results) == 10
    assert all(result.latency_ms > 0 and result.actual_cost_usd == 0 for result in results)
    assert all(control.results[result.run_id]["latencyMs"] > 0 for result in results)

