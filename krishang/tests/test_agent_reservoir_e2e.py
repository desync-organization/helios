import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helios.agency.head import HeadValidationError
from helios.agency.reservoir import AgentReservoir
from helios.api.app import create_app
from helios.config import Settings
from helios.contracts import (
    ArtifactType,
    Budget,
    ConsentScope,
    NormalizedTask,
    Plan,
    PlanNode,
    RuntimeMode,
    TaskType,
)
from helios.contracts.plan import NodeKind, SpawnRequest
from helios.control_plane import InMemoryControlPlane
from helios.execution import ExecutionServices
from helios.models import ModelManager, default_model_registry
from helios.runtime import DEFAULT_TOOLS, HeliosRuntime
from helios.scheduler import Scheduler
from helios.workspace import ArtifactStore


CATALOG_PATH = Path(__file__).resolve().parents[1] / "agents" / "baseline.yaml"
SPECIALISTS = {
    "html-slm": ("semantic accessible HTML", "htmlFixture"),
    "css-slm": ("responsive accessible CSS", "cssFixture"),
    "javascript-slm": ("browser JavaScript DOM behavior", "javascriptFixture"),
}


def _settings(tmp_path: Path) -> Settings:
    workspace = tmp_path / "workspace"
    return Settings(
        helios_workspace_root=workspace,
        helios_outbox_path=workspace / "outbox.jsonl",
        git_repo_cache_root=workspace / "repos",
        helios_agent_catalog=CATALOG_PATH,
        helios_writeback_mode="dry-run",
    )


def _reservoir(tmp_path: Path, *, snapshot: Path | None = None) -> AgentReservoir:
    settings = _settings(tmp_path)
    manager = ModelManager(default_model_registry(settings), settings.helios_max_vram_mb)
    return AgentReservoir.from_yaml(
        CATALOG_PATH,
        manager,
        model_backed=False,
        snapshot_path=snapshot,
    )


def _build_task(**metadata: str) -> NormalizedTask:
    return NormalizedTask(
        mode=RuntimeMode.BUILD,
        task_type=TaskType.FEATURE,
        repository="owner/web-app",
        base_sha="b" * 40,
        policy_version="policy-1",
        title="Build an accessible web experience",
        body="Create the requested frontend files.",
        consent=ConsentScope(repository_allowlisted=True),
        metadata=metadata,
    )


def _source_repository(tmp_path: Path, task: NormalizedTask) -> Path:
    source = tmp_path / f"source-{task.task_id}"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    (source / "README.md").write_text("# Web fixture\n", encoding="utf-8")
    (source / "tests").mkdir()
    (source / "tests" / "test_generated_web.py").write_text(
        "from pathlib import Path\n\n"
        "def test_generated_web_files_exist():\n"
        "    assert all(Path(name).is_file() for name in ('index.html', 'styles.css', 'app.js'))\n",
        encoding="utf-8",
    )
    (source / "pyproject.toml").write_text(
        "[project]\nname = \"web-fixture\"\nversion = \"0.0.1\"\n\n[tool.pytest.ini_options]\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(source), "-c", "user.name=Helios Test", "-c",
         "user.email=helios@example.invalid", "commit", "--quiet", "-m", "fixture"],
        check=True,
    )
    task.base_sha = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return source


def _specialist_plan(task: NormalizedTask, specialist: str) -> Plan:
    capability, _ = SPECIALISTS[specialist]
    tools = ["repo:read", "workspace:write"]
    return Plan(
        task_id=task.task_id,
        policy_version=task.policy_version,
        terminal_node_id="intent",
        nodes=[
            PlanNode(
                node_id="specialist",
                expert=specialist,
                output_artifact=ArtifactType.PATCH.value,
                acceptance_criteria=["Return one complete, valid specialist file"],
                tool_grants=tools,
                budget=Budget(max_tokens=3000, max_seconds=30),
                spawn=SpawnRequest(
                    name=specialist,
                    capability=capability,
                    base_model_id="google/gemma-3-1b-it",
                    tools=tools,
                ),
            ),
            PlanNode(
                node_id="critic",
                expert="critic",
                output_artifact=ArtifactType.CRITIC_VERDICT.value,
                dependencies=["specialist"],
                acceptance_criteria=["Independently validate the specialist artifact"],
                kind=NodeKind.CRITIC,
            ),
            PlanNode(
                node_id="intent",
                expert="intent",
                output_artifact=ArtifactType.WRITEBACK_INTENT.value,
                dependencies=["critic"],
                acceptance_criteria=["Emit a credential-free intent only after critic approval"],
                kind=NodeKind.INTENT,
            ),
        ],
    )


def test_yaml_catalog_loads_active_agents_and_spawnable_specialist_templates(tmp_path):
    reservoir = _reservoir(tmp_path)

    names = [agent.name for agent in reservoir.list()]
    assert len(names) == len(set(names))
    assert {"planner", "critic", "intent"} <= set(names)
    assert set(SPECIALISTS) <= set(names)
    assert set(SPECIALISTS).isdisjoint(reservoir.executable_names())
    for name in SPECIALISTS:
        specialist = reservoir.get(name)
        assert specialist.status == "template"
        assert specialist.model_id == "google/gemma-3-1b-it"
        assert specialist.adapter_id == f"gemma-{name.removesuffix('-slm')}-lora"
        assert specialist.modes == ["build"]
    assert reservoir.resolve("semantic accessible html", mode="build").name == "html-slm"


async def test_head_planner_receives_full_reservoir_metadata_including_templates(tmp_path):
    runtime = HeliosRuntime(settings=_settings(tmp_path), control_plane=InMemoryControlPlane())
    task = _build_task()
    seen_context = {}

    async def capture_catalog(context, repair):
        del repair
        seen_context.update(context)
        from helios.planning.fallback_templates import build_plan

        return build_plan(task).model_dump(mode="json")

    runtime.planner.generator = capture_catalog
    await runtime.planner.create_plan(task)

    catalog = {agent["name"]: agent for agent in seen_context["experts"]}
    assert set(SPECIALISTS) <= set(catalog)
    assert catalog["html-slm"] == {
        "name": "html-slm",
        "version": "1.0",
        "capability": "semantic accessible HTML document and component generation",
        "description": "Spawnable Gemma student specialized only for complete HTML output.",
        "modelId": "google/gemma-3-1b-it",
        "tools": ["repo:read", "workspace:write"],
        "modes": ["build"],
        "produces": ["patch"],
        "maxTokens": 3000,
        "maxSeconds": 90.0,
        "origin": "kickoff",
        "status": "template",
        "spawnable": True,
        "adapterId": "gemma-html-lora",
        "reservoirRevision": 1,
    }


def test_runtime_uses_reservoir_as_planner_and_scheduler_source_of_truth(tmp_path):
    runtime = HeliosRuntime(settings=_settings(tmp_path), control_plane=InMemoryControlPlane())

    assert runtime.experts == runtime.reservoir.handlers()
    assert runtime.plan_policy.registered_experts == runtime.reservoir.executable_names()
    assert runtime.plan_policy.allowed_tools == DEFAULT_TOOLS
    assert runtime.plan_policy.agent_catalog == runtime.reservoir.planner_catalog()
    assert "critic" in runtime.experts
    assert set(SPECIALISTS).isdisjoint(runtime.experts)


@pytest.mark.parametrize("specialist", list(SPECIALISTS))
async def test_spawned_web_specialist_executes_emits_birth_event_and_stores_head_validation(
    tmp_path,
    specialist,
):
    task = _build_task()
    control = InMemoryControlPlane()
    await control.enqueue(task)
    lease = await control.claim("head-orchestrator")
    reservoir = _reservoir(tmp_path, snapshot=tmp_path / "reservoir.json")
    store = ArtifactStore(tmp_path / "artifacts")
    source = _source_repository(tmp_path, task)
    scheduler = Scheduler(
        control_plane=control,
        artifact_store=store,
        experts=reservoir.handlers(),
        reservoir=reservoir,
        execution_services=ExecutionServices(task, tmp_path / "execution", source_repository=source),
    )

    result = await scheduler.execute(task, _specialist_plan(task, specialist), lease.lease_id)

    spawned = reservoir.get(specialist)
    assert spawned.status == "active"
    assert spawned.origin == "spawned"
    assert specialist in reservoir.executable_names()
    birth_events = [event for event in control.events.values() if event.type == "agent_spawned"]
    assert len(birth_events) == 1
    assert birth_events[0].payload["name"] == specialist
    assert birth_events[0].payload["modelId"] == "google/gemma-3-1b-it"
    artifact = result.artifacts["specialist"]
    assert artifact.producer == specialist
    assert artifact.content["headValidation"]["valid"] is True
    assert "complete-file-records" in artifact.content["headValidation"]["checks"]
    assert control.artifacts[artifact.artifact_id] == artifact
    assert store.get(artifact.artifact_id) == artifact
    assert any(event.type == "head_validation_passed" for event in control.events.values())


@pytest.mark.parametrize(
    ("specialist", "fixture_name", "invalid_output"),
    [
        ("html-slm", "htmlFixture", "<main>incomplete</main>"),
        ("css-slm", "cssFixture", "body { color: red;"),
        ("javascript-slm", "javascriptFixture", "eval('unsafe')"),
    ],
)
async def test_head_rejects_invalid_specialist_output_before_artifact_storage(
    tmp_path,
    specialist,
    fixture_name,
    invalid_output,
):
    task = _build_task(**{fixture_name: invalid_output})
    control = InMemoryControlPlane()
    await control.enqueue(task)
    lease = await control.claim("head-orchestrator")
    reservoir = _reservoir(tmp_path)
    source = _source_repository(tmp_path, task)
    scheduler = Scheduler(
        control_plane=control,
        artifact_store=ArtifactStore(tmp_path / "artifacts"),
        experts=reservoir.handlers(),
        reservoir=reservoir,
        execution_services=ExecutionServices(task, tmp_path / "execution", source_repository=source),
    )

    with pytest.raises(HeadValidationError):
        await scheduler.execute(task, _specialist_plan(task, specialist), lease.lease_id)

    assert not [artifact for artifact in control.artifacts.values() if artifact.producer == specialist]
    assert any(event.type == "plan_node_failed" for event in control.events.values())
    assert any(event.type == "run_failed" for event in control.events.values())
    assert not any(event.type == "head_validation_passed" for event in control.events.values())


def test_roles_api_exposes_the_same_full_catalog_seen_by_the_head(tmp_path):
    runtime = HeliosRuntime(settings=_settings(tmp_path), control_plane=InMemoryControlPlane())

    response = TestClient(create_app(runtime)).get("/roles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == "1.0"
    assert payload["roles"] == runtime.reservoir.planner_catalog()
    roles = {role["name"]: role for role in payload["roles"]}
    assert roles["html-slm"]["spawnable"] is True
    assert roles["html-slm"]["status"] == "template"
    assert roles["html-slm"]["adapterId"] == "gemma-html-lora"
    assert roles["critic"]["spawnable"] is False
    assert roles["critic"]["status"] == "active"


def test_spawned_agent_snapshot_persists_and_reloads_as_executable(tmp_path):
    snapshot = tmp_path / "state" / "agent-reservoir.json"
    reservoir = _reservoir(tmp_path, snapshot=snapshot)
    tools = ["repo:read", "workspace:write"]
    spawned, _ = reservoir.spawn(
        SpawnRequest(
            name="html-slm",
            capability="semantic accessible HTML",
            base_model_id="google/gemma-3-1b-it",
            tools=tools,
        ),
        run_id="run-first",
        budget_tokens=2000,
        budget_seconds=45,
        allowed_tools=set(tools),
    )
    assert snapshot.is_file()
    assert spawned.status == "active"

    restored = _reservoir(tmp_path, snapshot=snapshot)
    restored_agent = restored.get("html-slm")

    assert restored_agent.status == "active"
    assert restored_agent.origin == "spawned"
    assert restored_agent.spawned_by == "run-first"
    assert restored_agent.max_tokens == 2000
    assert restored_agent.max_seconds == 45
    assert "html-slm" in restored.executable_names()
    assert len([agent for agent in restored.list() if agent.name == "html-slm"]) == 1


async def test_head_spawns_all_three_slms_integrates_outputs_and_critic_validates(tmp_path):
    control = InMemoryControlPlane()
    runtime = HeliosRuntime(settings=_settings(tmp_path), control_plane=control)
    task = _build_task(useWebSlms=True)
    task.policy_pack["allowNoopAgents"] = ["backend"]
    task.consent.allowed_scanners = ["bandit"]
    source = _source_repository(tmp_path, task)
    await control.enqueue(task)
    lease = await control.claim("head-orchestrator")
    plan, events = await runtime.planner.create_plan(task)
    for event in events:
        await control.emit_event(event)
    services = ExecutionServices(task, tmp_path / "execution", source_repository=source)
    services._scanner_spec = lambda _scanner: [
        sys.executable,
        "-c",
        'print(\'{"results": []}\')',
    ]

    await Scheduler(
        control_plane=control,
        artifact_store=ArtifactStore(tmp_path / "artifacts"),
        experts=runtime.experts,
        reservoir=runtime.reservoir,
        execution_services=services,
        writeback_enabled=True,
    ).execute(task, plan, lease.lease_id)

    births = [event for event in control.events.values() if event.type == "agent_spawned"]
    assert {event.payload["name"] for event in births} == set(SPECIALISTS)
    package = next(artifact for artifact in control.artifacts.values()
                   if artifact.artifact_type == ArtifactType.PACKAGE_RESULT)
    assert {file["path"] for file in package.content["files"]} == {"index.html", "styles.css", "app.js"}
    manifest = next(artifact for artifact in control.artifacts.values()
                    if artifact.artifact_type == ArtifactType.BUILD_MANIFEST)
    assert {file["path"] for file in manifest.content["files"]} == {"index.html", "styles.css", "app.js"}
    critic = next(artifact for artifact in control.artifacts.values()
                  if artifact.artifact_type == ArtifactType.CRITIC_VERDICT)
    assert critic.content["verdict"] == "pass"
    assert critic.content["headValidation"]["valid"] is True
    assert len(control.intents) == 1
