from helios.contracts import ArtifactType, Budget, NormalizedTask, Plan, PlanNode, RuntimeMode, TaskType
from helios.contracts.plan import NodeKind, SpawnRequest


def _node(node_id: str, expert: str, output: ArtifactType, dependencies: list[str] | None = None,
          *, kind: NodeKind = NodeKind.EXPERT, tools: list[str] | None = None,
          seconds: float = 20, sensitive: bool = False,
          spawn: SpawnRequest | None = None) -> PlanNode:
    return PlanNode(
        node_id=node_id,
        expert=expert,
        output_artifact=output.value,
        dependencies=dependencies or [],
        acceptance_criteria=[f"produce a valid {output.value} artifact", "cite policy and upstream evidence"],
        tool_grants=tools or [],
        policy_ids=["runtime.typed-handoffs", "runtime.credential-free"],
        budget=Budget(max_tokens=1000, max_seconds=seconds),
        kind=kind,
        sensitive=sensitive,
        spawn=spawn,
    )


def maintain_plan(task: NormalizedTask) -> Plan:
    nodes: list[PlanNode]
    if task.task_type in {TaskType.FIX, TaskType.REPRO}:
        nodes = [
            _node("repro", "debug", ArtifactType.REPRO_REPORT, tools=["repo:read", "command:test"], seconds=90),
            _node("patch", "backend", ArtifactType.PATCH, ["repro"], tools=["repo:read", "workspace:write"], seconds=180, sensitive=True),
            _node("tests", "test", ArtifactType.TEST_RESULT, ["patch"], tools=["command:test"], seconds=180),
            _node("security", "security", ArtifactType.SECURITY_REPORT, ["patch"], tools=["scanner:local"], seconds=120, sensitive=True),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["patch", "tests", "security"], kind=NodeKind.CRITIC),
            _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
        ]
    elif task.task_type == TaskType.RELEASE:
        nodes = [
            _node("release", "docs", ArtifactType.RELEASE_DRAFT, tools=["repo:read"]),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["release"], kind=NodeKind.CRITIC),
            _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
        ]
    elif task.task_type == TaskType.REVIEW:
        nodes = [
            _node("review", "backend", ArtifactType.REVIEW_NOTES, tools=["repo:read"]),
            _node("security", "security", ArtifactType.SECURITY_REPORT, ["review"], tools=["scanner:local"], sensitive=True),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["review", "security"], kind=NodeKind.CRITIC),
            _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
        ]
    elif task.task_type == TaskType.DOCS:
        nodes = [
            _node("docs", "docs", ArtifactType.PATCH, tools=["repo:read", "workspace:write"]),
            _node("tests", "test", ArtifactType.TEST_RESULT, ["docs"], tools=["command:test"]),
            _node("security", "security", ArtifactType.SECURITY_REPORT, ["docs"], tools=["scanner:local"], sensitive=True),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["docs", "tests", "security"], kind=NodeKind.CRITIC),
            _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
        ]
    elif task.task_type == TaskType.ESCALATE:
        nodes = [
            _node("escalation", "triage", ArtifactType.ESCALATION),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["escalation"], kind=NodeKind.CRITIC),
            _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
        ]
    else:
        nodes = [
            _node("classify", "triage", ArtifactType.CLASSIFICATION),
            _node("dedupe", "dedupe", ArtifactType.DUP_REPORT),
            _node("reply", "docs", ArtifactType.DRAFT_REPLY, ["classify", "dedupe"]),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT,
                  ["classify", "dedupe", "reply"], kind=NodeKind.CRITIC),
            _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
        ]
    return Plan(task_id=task.task_id, policy_version=task.policy_version, nodes=nodes, terminal_node_id="intent", fallback=True)


def build_plan(task: NormalizedTask) -> Plan:
    nodes = [
        _node("requirements", "product", ArtifactType.REQUIREMENTS_SPEC, tools=["repo:read"]),
        _node("architecture", "architect", ArtifactType.ARCHITECTURE_DECISION, ["requirements"], tools=["repo:read"]),
    ]
    requested = task.metadata.get("webSlms", [])
    if task.metadata.get("useWebSlms") and not requested:
        requested = ["html", "css", "javascript"]
    web_nodes: list[str] = []
    for language in requested:
        normalized = str(language).lower()
        if normalized not in {"html", "css", "javascript"}:
            raise ValueError(f"unsupported web SLM specialist: {language}")
        expert = f"{normalized}-slm"
        node_id = f"slm-{normalized}"
        tools = ["repo:read", "workspace:write"]
        nodes.append(_node(
            node_id, expert, ArtifactType.PATCH, ["architecture"], tools=tools, seconds=90,
            spawn=SpawnRequest(name=expert, capability=f"specialized {normalized} generation",
                               base_model_id="google/gemma-3-1b-it", tools=tools),
        ))
        web_nodes.append(node_id)
    if not web_nodes:
        nodes.append(_node("web", "web-typescript", ArtifactType.PATCH, ["architecture"],
                           tools=["repo:read", "workspace:write"], seconds=180))
        web_nodes.append("web")
    nodes.extend([
        _node("backend", "backend", ArtifactType.PATCH, ["architecture"], tools=["repo:read", "workspace:write"], seconds=180),
        _node("integration", "integration", ArtifactType.PACKAGE_RESULT, [*web_nodes, "backend"], kind=NodeKind.INTEGRATION, tools=["workspace:write", "command:test"], seconds=240),
        _node("tests", "test", ArtifactType.TEST_RESULT, ["integration"], tools=["command:test"], seconds=180),
        _node("security", "security", ArtifactType.SECURITY_REPORT, ["integration"], tools=["scanner:local"], sensitive=True),
        _node("manifest", "integration", ArtifactType.BUILD_MANIFEST, ["integration", "tests", "security"]),
        _node("critic", "critic", ArtifactType.CRITIC_VERDICT,
              ["manifest", "integration", "tests", "security"], kind=NodeKind.CRITIC),
        _node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT),
    ])
    return Plan(task_id=task.task_id, policy_version=task.policy_version, nodes=nodes, terminal_node_id="intent", fallback=True)


def security_plan(task: NormalizedTask) -> Plan:
    task.assert_authorized()
    nodes = [
        _node("inventory", "security", ArtifactType.REPOSITORY_INVENTORY, tools=["repo:read"], sensitive=True),
        _node("dependencies", "security", ArtifactType.DEPENDENCY_INVENTORY, ["inventory"], tools=["scanner:local"], seconds=120, sensitive=True),
        _node("scan", "security", ArtifactType.SARIF_REPORT, ["inventory"], tools=["scanner:local"], seconds=300, sensitive=True),
        _node("analysis", "security", ArtifactType.SECURITY_REPORT, ["dependencies", "scan"], sensitive=True),
    ]
    if task.task_type == TaskType.REMEDIATE:
        nodes.extend([
            _node("remediation", "security", ArtifactType.REMEDIATION_PLAN, ["analysis"], sensitive=True),
            _node("patch", "backend", ArtifactType.PATCH, ["remediation"], tools=["repo:read", "workspace:write"], sensitive=True),
            _node("tests", "test", ArtifactType.TEST_RESULT, ["patch"], tools=["command:test"]),
            _node("rescan", "security", ArtifactType.SARIF_REPORT, ["patch"], tools=["scanner:local"], sensitive=True),
            _node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["patch", "tests", "rescan"], kind=NodeKind.CRITIC),
        ])
    else:
        nodes.append(_node("critic", "critic", ArtifactType.CRITIC_VERDICT, ["analysis"], kind=NodeKind.CRITIC))
    nodes.append(_node("intent", "intent", ArtifactType.WRITEBACK_INTENT, ["critic"], kind=NodeKind.INTENT))
    return Plan(task_id=task.task_id, policy_version=task.policy_version, nodes=nodes, terminal_node_id="intent", fallback=True)


def fallback_plan(task: NormalizedTask) -> Plan:
    if task.mode == RuntimeMode.BUILD:
        return build_plan(task)
    if task.mode == RuntimeMode.SECURITY_AUDIT:
        return security_plan(task)
    return maintain_plan(task)
