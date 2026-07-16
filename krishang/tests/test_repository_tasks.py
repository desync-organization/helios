import pytest

from helios.contracts import ConsentScope, NormalizedTask, RuntimeMode, TaskType
from helios.execution import ExecutionPolicyError
from helios.workspace.repository_tasks import prepare_repository_build


async def test_live_build_preparation_requires_public_or_brokered_source(tmp_path):
    task = NormalizedTask(
        mode=RuntimeMode.BUILD,
        task_type=TaskType.FEATURE,
        repository="owner/repository",
        base_sha="a" * 40,
        policy_version="p1",
        title="Implement the requested repository feature",
        source="github",
        consent=ConsentScope(repository_allowlisted=True, network_permitted=False),
    )

    with pytest.raises(ExecutionPolicyError, match="brokered snapshot"):
        await prepare_repository_build(task, tmp_path)

    assert "proposedFiles" not in task.metadata


def test_hard_coded_status_bar_builder_is_not_exported():
    import helios.workspace.repository_tasks as repository_tasks

    assert not hasattr(repository_tasks, "_homepage_files")
    assert not hasattr(repository_tasks, "RUNTIME_STATUS_BAR")
