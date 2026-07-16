import asyncio
import json
import tempfile
from pathlib import Path

from helios.config import Settings
from helios.contracts import ArtifactType
from helios.control_plane import InMemoryControlPlane
from helios.demo.fixtures import demo_tasks
from helios.runtime import HeliosRuntime
from helios.workspace.commands import SafeCommandRunner


async def _run_git(runner: SafeCommandRunner, argv: list[str]) -> str:
    result = await runner.run(["git", *argv], timeout=30)
    if result.exit_code:
        detail = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError(f"could not prepare the offline demo repository: {detail}")
    return result.stdout.strip()


async def _demo_repository(root: Path) -> tuple[Path, str]:
    source = root / "source"
    source.mkdir()
    (source / "src").mkdir()
    (source / "src" / "app.py").write_text("STATUS = \"ready\"\n", encoding="utf-8")
    (source / "README.md").write_text("# Helios offline demo\n", encoding="utf-8")
    (source / "pyproject.toml").write_text(
        "[project]\nname = \"helios-demo-fixture\"\nversion = \"0.0.1\"\n\n"
        "[tool.pytest.ini_options]\npythonpath = [\".\"]\n",
        encoding="utf-8",
    )
    (source / "tests").mkdir()
    (source / "tests" / "test_generated_web.py").write_text(
        "from pathlib import Path\n\n"
        "def test_generated_web_files_exist():\n"
        "    for name in (\"index.html\", \"styles.css\", \"app.js\"):\n"
        "        Path(name).read_text(encoding=\"utf-8\")\n",
        encoding="utf-8",
    )
    runner = SafeCommandRunner(root, {"git"})
    await _run_git(runner, ["init", "--quiet", "source"])
    await _run_git(runner, ["-C", "source", "add", "."])
    await _run_git(runner, [
        "-C", "source", "-c", "user.name=Helios Demo",
        "-c", "user.email=helios@example.invalid", "commit", "--quiet",
        "-m", "Create offline demo fixture",
    ])
    sha = await _run_git(runner, ["-C", "source", "rev-parse", "HEAD"])
    return source, sha


async def seed() -> dict:
    with tempfile.TemporaryDirectory(prefix="helios-demo-") as directory:
        root = Path(directory)
        source, sha = await _demo_repository(root)
        settings = Settings(
            environment="test",
            control_plane_url="",
            worker_url="",
            convex_http_url="",
            helios_workspace_root=root / "workspace",
            git_repo_cache_root=root / "repos",
            helios_outbox_path=root / "outbox.jsonl",
            helios_inference_mode="deterministic",
            helios_writeback_mode="dry-run",
        )
        control = InMemoryControlPlane()
        runtime = HeliosRuntime(
            settings,
            control,
            source_repositories={"demo/helios": source},
        )
        tasks = demo_tasks()
        for task in tasks:
            task.base_sha = sha
            await control.enqueue(task)
        while await runtime.process_once():
            pass
        intents = [
            item.content
            for item in control.artifacts.values()
            if item.artifact_type == ArtifactType.WRITEBACK_INTENT
            and item.content.get("authorized") is True
        ]
        return {
            "runs": len(control.results),
            "artifacts": len(control.artifacts),
            "intents": intents,
            "submittedIntents": len(control.intents),
            "events": len(control.events),
            "provenance": "dry-run",
        }


def main() -> None:
    print(json.dumps(asyncio.run(seed()), indent=2))


if __name__ == "__main__":
    main()
