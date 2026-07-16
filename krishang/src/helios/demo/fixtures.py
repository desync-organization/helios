from helios.contracts import ConsentScope, NormalizedTask, RuntimeMode, TaskType


def demo_tasks() -> list[NormalizedTask]:
    allow = ConsentScope(repository_allowlisted=True)
    return [
        NormalizedTask(mode=RuntimeMode.MAINTAIN, task_type=TaskType.CLASSIFY,
                       repository="demo/helios", base_sha="0" * 40, policy_version="demo-v1",
                       title="Bug: status endpoint fails", body="The status endpoint returns an error.", consent=allow),
        NormalizedTask(mode=RuntimeMode.BUILD, task_type=TaskType.FEATURE,
                       repository="demo/helios", base_sha="0" * 40, policy_version="demo-v1",
                       title="Add a bounded status API", body="Add a read-only status endpoint with tests.",
                       consent=ConsentScope(repository_allowlisted=True, allowed_scanners=["bandit"]),
                       policy_pack={"allowNoopAgents": ["backend"]},
                       metadata={"acceptanceCriteria": ["endpoint returns runtime state", "tests pass"],
                                 "useWebSlms": True}),
        NormalizedTask(mode=RuntimeMode.SECURITY_AUDIT, task_type=TaskType.AUDIT,
                       repository="demo/helios", base_sha="0" * 40, policy_version="demo-v1",
                       title="Read-only repository audit", consent=ConsentScope(repository_allowlisted=True, security_audit_opt_in=True,
                       allowed_scanners=["bandit"]), metadata={"languages": ["Python"], "manifests": ["pyproject.toml"]}),
    ]
