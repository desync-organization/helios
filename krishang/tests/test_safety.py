import sys

import pytest

from helios.contracts import ConsentScope, NormalizedTask, RuntimeMode, TaskType
from helios.security.redaction import redact_text
from helios.workspace.commands import SafeCommandRunner
from helios.workspace.repositories import RepositoryNamespace, safe_join


def test_path_traversal_rejected(tmp_path):
    with pytest.raises(ValueError, match="traversal"):
        safe_join(tmp_path, "..", "escape")


async def test_command_allowlist_and_failure_are_authoritative(tmp_path):
    runner = SafeCommandRunner(tmp_path, {sys.executable})
    result = await runner.run([sys.executable, "-c", "raise SystemExit(3)"])
    assert result.exit_code == 3
    with pytest.raises(PermissionError):
        await runner.run(["not-allowed"])


def test_redaction_removes_tokens_and_paths():
    output = redact_text("token=ghp_abcdefghijklmnopqrstuvwxyz123456 C:\\Users\\person\\secret.txt")
    assert "ghp_" not in output and "person" not in output
    assert "[REDACTED]" in output and "[LOCAL_PATH]" in output


def test_repository_namespaces_are_isolated(tmp_path):
    left = RepositoryNamespace(tmp_path, "owner/a", "issue-1").create()
    right = RepositoryNamespace(tmp_path, "owner/b", "issue-1").create()
    assert left.root != right.root


def test_external_exploit_rejected_before_execution():
    task = NormalizedTask(mode=RuntimeMode.SECURITY_AUDIT, task_type=TaskType.AUDIT,
                          repository="owner/repo", base_sha="a" * 40, policy_version="p1", title="scan target",
                          consent=ConsentScope(repository_allowlisted=True, security_audit_opt_in=True),
                          metadata={"externalTarget": True, "exploitRequested": True})
    with pytest.raises(ValueError, match="forbidden"):
        task.assert_authorized()


def test_remediation_requires_separate_consent():
    task = NormalizedTask(mode=RuntimeMode.SECURITY_AUDIT, task_type=TaskType.REMEDIATE,
                          repository="owner/repo", base_sha="a" * 40, policy_version="p1", title="fix",
                          consent=ConsentScope(repository_allowlisted=True, security_audit_opt_in=True))
    with pytest.raises(ValueError, match="separate authorization"):
        task.assert_authorized()

