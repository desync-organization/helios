import pytest

from helios.contracts import ConsentScope, NormalizedTask, RuntimeMode, TaskType


@pytest.fixture
def maintain_task() -> NormalizedTask:
    return NormalizedTask(mode=RuntimeMode.MAINTAIN, task_type=TaskType.CLASSIFY,
                          repository="owner/repo", base_sha="a" * 40, policy_version="p1",
                          title="Bug: endpoint fails", body="It returns an error",
                          consent=ConsentScope(repository_allowlisted=True))

