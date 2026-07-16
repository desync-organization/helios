import hashlib
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from helios.contracts import ArtifactType, Budget, ConsentScope, NormalizedTask, PlanNode, RuntimeMode, TaskType
from helios.execution import ExecutionPolicyError, ExecutionServices


def _repository(
    root: Path,
    *,
    passing_tests: bool = False,
    test_side_effect: bool = False,
    gitignore: str | None = None,
) -> tuple[Path, str]:
    source = root / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    (source / "src").mkdir()
    (source / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "README.md").write_text("# Fixture\n", encoding="utf-8")
    if gitignore is not None:
        (source / ".gitignore").write_text(gitignore, encoding="utf-8")
    if passing_tests:
        (source / "tests").mkdir()
        side_effect = (
            "    Path('test-side-effect.txt').write_text('changed', encoding='utf-8')\n"
            if test_side_effect
            else ""
        )
        (source / "tests" / "test_app.py").write_text(
            "from pathlib import Path\n\n"
            "from src.app import VALUE\n\n"
            "def test_value():\n"
            f"{side_effect}"
            "    assert VALUE == 1\n",
            encoding="utf-8",
        )
        (source / "pyproject.toml").write_text(
            "[project]\nname = \"fixture\"\nversion = \"0.0.1\"\n\n[tool.pytest.ini_options]\npythonpath = [\".\"]\n",
            encoding="utf-8",
        )
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(source), "-c", "user.name=Helios Test", "-c", "user.email=helios@example.invalid",
         "commit", "--quiet", "-m", "fixture"],
        check=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return source, sha


def _task(sha: str, **consent_updates) -> NormalizedTask:
    consent = ConsentScope(repository_allowlisted=True, **consent_updates)
    return NormalizedTask(
        mode=RuntimeMode.MAINTAIN,
        task_type=TaskType.FIX,
        repository="owner/repository",
        base_sha=sha,
        policy_version="p1",
        title="Fix the fixture",
        source="local",
        consent=consent,
    )


async def test_repository_reads_and_patch_materialization_are_isolated_and_scoped(tmp_path):
    source, sha = _repository(tmp_path)
    task = _task(sha)
    services = ExecutionServices(task, tmp_path / "workspace", source_repository=source)
    evidence = await services.repository_evidence()

    assert evidence["isolated"] is True
    assert evidence["commitSha"] == sha
    assert services.checkout != source

    node = PlanNode(
        node_id="patch",
        expert="backend",
        output_artifact=ArtifactType.PATCH.value,
        acceptance_criteria=["complete file"],
        tool_grants=["workspace:write"],
        budget=Budget(max_seconds=30),
    )
    context = services.for_node(node)
    content = {"files": [{"path": "src/new.py", "content": "VALUE = 2\n"}], "completeFiles": True}
    assert context.validate_output_scope(content)
    result = await context.commit_validated_output(content)

    assert result and result["appliedToWorktree"] is True
    assert (services.checkout / "src" / "new.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    assert not (source / "src" / "new.py").exists()

    protected = {"files": [{"path": ".github/workflows/release.yml", "content": "name: unsafe\n"}]}
    with pytest.raises(ExecutionPolicyError, match="protected path"):
        context.validate_output_scope(protected)


async def test_repository_evidence_uses_git_tracked_and_untracked_source_files(
    tmp_path,
    monkeypatch,
):
    source, sha = _repository(tmp_path, gitignore="ignored/\n")
    services = ExecutionServices(_task(sha), tmp_path / "workspace", source_repository=source)
    await services.materialize_repository()
    untracked = services.checkout / "untracked.txt"
    untracked.write_text("visible\n", encoding="utf-8")
    ignored = services.checkout / "ignored"
    ignored.mkdir()
    (ignored / "bulk.js").write_text("ignored\n", encoding="utf-8")

    def reject_fallback(_path: Path, _pattern: str):
        raise AssertionError("Git checkout unexpectedly used the filesystem fallback")

    monkeypatch.setattr(Path, "rglob", reject_fallback)
    evidence = await services.repository_evidence()

    files = {item["path"]: item for item in evidence["files"]}
    assert set(files) == {".gitignore", "README.md", "src/app.py", "untracked.txt"}
    assert "ignored/bulk.js" not in files
    assert files["untracked.txt"] == {
        "path": "untracked.txt",
        "bytes": len(untracked.read_bytes()),
        "sha256": hashlib.sha256(untracked.read_bytes()).hexdigest(),
    }
    assert next(item for item in evidence["excerpts"] if item["path"] == "README.md")[
        "content"
    ] == "# Fixture\n"


async def test_repository_evidence_non_git_fallback_runs_off_event_loop(
    tmp_path,
    monkeypatch,
):
    services = ExecutionServices(
        _task("0" * 40, excluded_paths=["ignored/**"]),
        tmp_path / "workspace",
    )
    services.checkout.mkdir(parents=True)
    plain = services.checkout / "plain.txt"
    plain.write_text("fallback\n", encoding="utf-8")
    ignored = services.checkout / "ignored"
    ignored.mkdir()
    (ignored / "hidden.txt").write_text("hidden\n", encoding="utf-8")
    caller_thread = threading.get_ident()
    evidence_threads: list[int] = []
    collect = services._collect_repository_evidence

    async def materialized():
        return services._materialization_evidence("0" * 40, "fixture")

    def tracked_collect():
        evidence_threads.append(threading.get_ident())
        return collect()

    monkeypatch.setattr(services, "materialize_repository", materialized)
    monkeypatch.setattr(services, "_collect_repository_evidence", tracked_collect)

    evidence = await services.repository_evidence()

    assert evidence_threads and evidence_threads[0] != caller_thread
    assert [item["path"] for item in evidence["files"]] == ["plain.txt"]
    assert evidence["files"][0]["sha256"] == hashlib.sha256(plain.read_bytes()).hexdigest()
    assert evidence["excerpts"] == [{"path": "plain.txt", "content": "fallback\n"}]


async def test_test_evidence_comes_from_a_real_sanitized_process(tmp_path):
    source, sha = _repository(tmp_path, passing_tests=True)
    services = ExecutionServices(_task(sha), tmp_path / "workspace", source_repository=source)
    node = PlanNode(
        node_id="tests",
        expert="test",
        output_artifact=ArtifactType.TEST_RESULT.value,
        acceptance_criteria=["run repository tests"],
        tool_grants=["command:test"],
        budget=Budget(max_seconds=60),
    )

    evidence = await services.for_node(node).test_evidence()

    assert evidence["authoritative"] is True
    assert evidence["fabricated"] is False
    assert evidence["success"] is True
    assert evidence["results"][0]["commandHash"]
    assert evidence["results"][0]["exitCode"] == 0
    assert not list(services.checkout.rglob("*.pyc"))


async def test_test_evidence_rejects_meaningful_worktree_mutation(tmp_path):
    source, sha = _repository(tmp_path, passing_tests=True, test_side_effect=True)
    services = ExecutionServices(_task(sha), tmp_path / "workspace", source_repository=source)
    node = PlanNode(
        node_id="tests",
        expert="test",
        output_artifact=ArtifactType.TEST_RESULT.value,
        acceptance_criteria=["run repository tests"],
        tool_grants=["command:test"],
        budget=Budget(max_seconds=60),
    )

    with pytest.raises(ExecutionPolicyError, match="modified the task worktree"):
        await services.for_node(node).test_evidence()

    assert (services.checkout / "test-side-effect.txt").read_text(encoding="utf-8") == "changed"


async def test_configured_scanner_output_is_executed_normalized_and_redacted(tmp_path, monkeypatch):
    source, sha = _repository(tmp_path)
    task = NormalizedTask(
        mode=RuntimeMode.SECURITY_AUDIT,
        task_type=TaskType.AUDIT,
        repository="owner/repository",
        base_sha=sha,
        policy_version="p1",
        title="Audit fixture",
        source="local",
        consent=ConsentScope(
            repository_allowlisted=True,
            security_audit_opt_in=True,
            allowed_scanners=["bandit"],
        ),
    )
    services = ExecutionServices(task, tmp_path / "workspace", source_repository=source)
    scanner_payload = {
        "results": [{
            "test_id": "B999",
            "issue_text": "Example defensive finding",
            "issue_severity": "HIGH",
            "issue_confidence": "HIGH",
            "filename": "src/app.py",
            "line_number": 1,
            "code": "token=ghp_abcdefghijklmnopqrstuvwxyz123456",
        }],
    }
    monkeypatch.setattr(
        services,
        "_scanner_spec",
        lambda _scanner: [sys.executable, "-c", f"print({json.dumps(json.dumps(scanner_payload))})"],
    )
    node = PlanNode(
        node_id="scan",
        expert="security",
        output_artifact=ArtifactType.SARIF_REPORT.value,
        acceptance_criteria=["run configured scanner"],
        tool_grants=["scanner:local"],
        budget=Budget(max_seconds=60),
    )

    evidence = await services.for_node(node).scanner_evidence()

    assert evidence["coverageComplete"] is True
    assert evidence["scannerResults"][0]["status"] == "completed"
    assert evidence["findings"][0]["ruleId"] == "B999"
    assert "ghp_" not in json.dumps(evidence)
