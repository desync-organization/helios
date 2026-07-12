import pytest

from helios.contracts import ArtifactType, ConsentScope, NormalizedTask, RuntimeMode, TaskType
from helios.planning.fallback_templates import build_plan, maintain_plan, security_plan


@pytest.mark.parametrize("task_type,expected", [
    (TaskType.INTAKE, ArtifactType.CLASSIFICATION),
    (TaskType.CLASSIFY, ArtifactType.CLASSIFICATION),
    (TaskType.LABEL, ArtifactType.CLASSIFICATION),
    (TaskType.DEDUPE, ArtifactType.DUP_REPORT),
    (TaskType.CLARIFY, ArtifactType.DRAFT_REPLY),
    (TaskType.RESPOND, ArtifactType.DRAFT_REPLY),
    (TaskType.REPRO, ArtifactType.REPRO_REPORT),
    (TaskType.FIX, ArtifactType.PATCH),
    (TaskType.REVIEW, ArtifactType.REVIEW_NOTES),
    (TaskType.DOCS, ArtifactType.PATCH),
    (TaskType.RELEASE, ArtifactType.RELEASE_DRAFT),
    (TaskType.ESCALATE, ArtifactType.ESCALATION),
])
def test_every_maintainer_task_has_declared_artifact(task_type, expected):
    task = NormalizedTask(mode=RuntimeMode.MAINTAIN, task_type=task_type, repository="owner/repo",
                          base_sha="a" * 40, policy_version="p1", title="task",
                          consent=ConsentScope(repository_allowlisted=True))
    outputs = {ArtifactType(node.output_artifact) for node in maintain_plan(task).nodes}
    assert expected in outputs
    assert ArtifactType.CRITIC_VERDICT in outputs and ArtifactType.WRITEBACK_INTENT in outputs


def test_builder_has_parallel_specialists_integration_and_gates():
    task = NormalizedTask(mode=RuntimeMode.BUILD, task_type=TaskType.FEATURE, repository="owner/repo",
                          base_sha="a" * 40, policy_version="p1", title="feature",
                          consent=ConsentScope(repository_allowlisted=True))
    plan = build_plan(task)
    nodes = {item.node_id: item for item in plan.nodes}
    assert nodes["web"].dependencies == nodes["backend"].dependencies == ["architecture"]
    assert set(nodes["integration"].dependencies) == {"web", "backend"}
    assert {"tests", "security"} <= set(nodes)
    assert nodes["intent"].dependencies == ["critic"]


def test_security_read_only_plan_has_no_patch():
    task = NormalizedTask(mode=RuntimeMode.SECURITY_AUDIT, task_type=TaskType.AUDIT, repository="owner/repo",
                          base_sha="a" * 40, policy_version="p1", title="audit",
                          consent=ConsentScope(repository_allowlisted=True, security_audit_opt_in=True))
    outputs = {node.output_artifact for node in security_plan(task).nodes}
    assert ArtifactType.PATCH.value not in outputs
    assert ArtifactType.REPOSITORY_INVENTORY.value in outputs
    assert ArtifactType.SARIF_REPORT.value in outputs


def test_security_remediation_has_patch_test_and_rescan():
    task = NormalizedTask(mode=RuntimeMode.SECURITY_AUDIT, task_type=TaskType.REMEDIATE, repository="owner/repo",
                          base_sha="a" * 40, policy_version="p1", title="remediate",
                          consent=ConsentScope(repository_allowlisted=True, security_audit_opt_in=True,
                                               remediation_permitted=True))
    plan = security_plan(task)
    assert {"remediation", "patch", "tests", "rescan", "critic", "intent"} <= {node.node_id for node in plan.nodes}

