from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from helios.contracts import Artifact, ArtifactType, NormalizedTask, PlanNode

if TYPE_CHECKING:
    from helios.execution import NodeExecutionContext


@dataclass(slots=True)
class ExpertContext:
    task: NormalizedTask
    run_id: str
    node: PlanNode
    upstream: list[Artifact]
    revision_notes: list[str]
    execution: "NodeExecutionContext | None" = None


ExpertHandler = Callable[[ExpertContext], Awaitable[dict[str, Any]]]


def _upstream_summary(context: ExpertContext) -> list[dict[str, str]]:
    return [{"artifactId": item.artifact_id, "type": item.artifact_type.value, "hash": item.content_hash} for item in context.upstream]


def deterministic_gate_failures(context: ExpertContext) -> list[Artifact]:
    failures: list[Artifact] = []
    read_only_audit = context.task.mode.value == "security_audit" and context.task.task_type.value == "audit"
    for artifact in context.upstream:
        if artifact.artifact_type == ArtifactType.TEST_RESULT and artifact.content.get("success") is not True:
            failures.append(artifact)
        elif artifact.artifact_type == ArtifactType.SECURITY_REPORT:
            if artifact.content.get("coverageComplete") is not True:
                failures.append(artifact)
            elif not read_only_audit and artifact.content.get("safe") is not True:
                failures.append(artifact)
        elif artifact.artifact_type == ArtifactType.SARIF_REPORT and context.task.task_type.value == "remediate":
            if artifact.content.get("coverageComplete") is not True or artifact.content.get("findings"):
                failures.append(artifact)
        elif artifact.artifact_type == ArtifactType.PACKAGE_RESULT and artifact.content.get("integrated") is not True:
            failures.append(artifact)
    return failures


async def deterministic_expert(context: ExpertContext) -> dict[str, Any]:
    output = ArtifactType(context.node.output_artifact)
    task = context.task
    evidence = _upstream_summary(context)
    base = {"taskId": task.task_id, "repository": task.repository, "baseSha": task.base_sha,
            "evidence": evidence, "policyIds": context.node.policy_ids}
    if "repo:read" in context.node.tool_grants:
        if not context.execution:
            raise RuntimeError("repository access requires a scheduler-bound execution context")
        base["repositoryEvidence"] = await context.execution.repository_evidence()
    if context.node.expert == "html-slm":
        return {**base, "language": "html", "files": [{"path": "index.html", "content": task.metadata.get(
            "htmlFixture", "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Helios</title></head><body><main id=\"app\"></main></body></html>"
        )}], "completeFiles": True}
    if context.node.expert == "css-slm":
        return {**base, "language": "css", "files": [{"path": "styles.css", "content": task.metadata.get(
            "cssFixture", ":root { color-scheme: dark; }\nbody { margin: 0; background: #0c0c0c; color: #e6f0ff; }"
        )}], "completeFiles": True}
    if context.node.expert == "javascript-slm":
        return {**base, "language": "javascript", "files": [{"path": "app.js", "content": task.metadata.get(
            "javascriptFixture", "const app = document.querySelector('#app');\nif (app) app.textContent = 'Ready';"
        )}], "completeFiles": True}
    if output == ArtifactType.CLASSIFICATION:
        lowered = f"{task.title} {task.body}".lower()
        label = "bug" if any(word in lowered for word in ("bug", "error", "fails", "broken")) else "question"
        return {**base, "classification": label, "priority": "p2", "labels": [label], "confidence": 0.86}
    if output == ArtifactType.DUP_REPORT:
        return {**base, "candidates": [], "isExactDuplicate": False, "threshold": 0.92}
    if output == ArtifactType.DRAFT_REPLY:
        return {**base, "body": f"Thanks for reporting this. Helios reviewed `{task.title}` and recorded the evidence for maintainer follow-up.",
                "sourceLinks": task.metadata.get("sourceLinks", [])}
    if output == ArtifactType.REPRO_REPORT:
        if not context.execution:
            raise RuntimeError("reproduction requires a scheduler-bound execution context")
        result = await context.execution.test_evidence()
        return {**base, "isolated": True,
                "reproduced": result["executed"] and not result["success"],
                "commands": result["commands"], "results": result["results"],
                "authoritative": True, "fabricated": False,
                "smallestFailingCase": task.title}
    if output == ArtifactType.PATCH:
        configured = task.policy_pack.get("deterministicFilesByAgent", {})
        files = configured.get(context.node.expert, []) if isinstance(configured, dict) else []
        allowed_noops = task.policy_pack.get("allowNoopAgents", [])
        no_changes = not files and isinstance(allowed_noops, list) and context.node.expert in allowed_noops
        return {**base, "format": "structured-patch", "baseSha": task.base_sha,
                "files": files, "completeFiles": bool(files) or no_changes,
                "noChangesRequired": no_changes,
                "protectedPathsTouched": False, "fabricated": False}
    if output == ArtifactType.TEST_RESULT:
        if not context.execution:
            raise RuntimeError("tests require a scheduler-bound execution context")
        result = await context.execution.test_evidence()
        return {**base, **result, "before": "unknown", "after": result["status"]}
    if output == ArtifactType.SECURITY_REPORT:
        if not context.execution:
            raise RuntimeError("security review requires a scheduler-bound execution context")
        return {**base, **await context.execution.security_evidence(context.upstream)}
    if output == ArtifactType.REVIEW_NOTES:
        return {**base, "summary": "Evidence-backed review completed", "findings": [],
                "mergeEligible": False, "reason": "merge eligibility is evaluated by the control plane"}
    if output == ArtifactType.ESCALATION:
        return {**base, "whatITried": task.metadata.get("whatITried", "classified the request and checked policy"),
                "exactFailure": task.metadata.get("exactFailure", task.body or task.title),
                "smallestFailingCase": task.metadata.get("smallestFailingCase", task.title),
                "artifactChain": [item["artifactId"] for item in evidence],
                "decisionNeeded": task.metadata.get("decisionNeeded", "maintainer decision required")}
    if output == ArtifactType.RELEASE_DRAFT:
        return {**base, "draft": True, "published": False, "notes": task.body or task.title}
    if output == ArtifactType.REQUIREMENTS_SPEC:
        missing = [decision for decision in ("authentication", "payments", "deployment", "data retention")
                   if decision in task.body.lower() and decision not in task.metadata.get("approvedDecisions", [])]
        return {**base, "goals": [task.title], "nonGoals": ["Unapproved infrastructure or production changes"],
                "userStories": [task.body or task.title], "constraints": ["preserve repository conventions"],
                "acceptanceCriteria": task.metadata.get("acceptanceCriteria", ["relevant tests pass"]),
                "unansweredDecisions": missing, "repositoryCitations": task.metadata.get("repositoryCitations", [])}
    if output == ArtifactType.ARCHITECTURE_DECISION:
        return {**base, "alternatives": ["extend existing patterns", "introduce a new subsystem"],
                "chosenApproach": "extend existing repository patterns", "affectedModules": task.metadata.get("affectedModules", []),
                "dataFlow": "request → existing service boundary → tested result", "migrationImpact": "none unless approved",
                "testPlan": task.metadata.get("testCommands", ["repository-declared full suite"]),
                "securityConsiderations": ["least privilege", "no credentials in runtime"], "rollback": "revert the isolated branch"}
    if output == ArtifactType.PACKAGE_RESULT:
        files: list[dict[str, Any]] = []
        owners: dict[str, str] = {}
        conflicts: list[dict[str, str]] = []
        for artifact in context.upstream:
            for file_record in artifact.content.get("files", []):
                path = str(file_record.get("path", ""))
                if path in owners:
                    conflicts.append({"path": path, "firstArtifact": owners[path],
                                      "secondArtifact": artifact.artifact_id})
                else:
                    owners[path] = artifact.artifact_id
                    files.append(file_record)
        return {**base, "integrated": not conflicts, "conflicts": conflicts,
                "files": files, "sourceArtifacts": list(owners.values()), "baseSha": task.base_sha}
    if output == ArtifactType.BUILD_MANIFEST:
        integrated_files = [file for item in context.upstream if item.artifact_type == ArtifactType.PACKAGE_RESULT
                            for file in item.content.get("files", [])]
        workspace = await context.execution.workspace_evidence() if context.execution else {}
        return {**base, "files": integrated_files,
                "commands": [command for item in context.upstream if item.artifact_type == ArtifactType.TEST_RESULT
                             for command in item.content.get("commands", [])],
                "testResults": [item.content for item in context.upstream if item.artifact_type == ArtifactType.TEST_RESULT],
                "securityResults": [item.content for item in context.upstream if item.artifact_type == ArtifactType.SECURITY_REPORT],
                "knownLimitations": [], "workspaceEvidence": workspace,
                "resultHashes": {item.artifact_id: item.content_hash for item in context.upstream}}
    if output == ArtifactType.REPOSITORY_INVENTORY:
        if not context.execution:
            raise RuntimeError("inventory requires a scheduler-bound execution context")
        return {**base, **await context.execution.inventory_evidence()}
    if output == ArtifactType.DEPENDENCY_INVENTORY:
        if not context.execution:
            raise RuntimeError("dependency inventory requires a scheduler-bound execution context")
        return {**base, **await context.execution.dependency_evidence()}
    if output == ArtifactType.SARIF_REPORT:
        if not context.execution:
            raise RuntimeError("scanner execution requires a scheduler-bound execution context")
        return {**base, **await context.execution.scanner_evidence()}
    if output == ArtifactType.REMEDIATION_PLAN:
        if not context.execution:
            raise RuntimeError("remediation planning requires a scheduler-bound execution context")
        return {**base, **await context.execution.remediation_evidence(context.upstream)}
    if output == ArtifactType.CRITIC_VERDICT:
        failed = deterministic_gate_failures(context)
        unanswered = [decision for item in context.upstream for decision in item.content.get("unansweredDecisions", [])]
        reviewed = context.upstream[0] if context.upstream else None
        reviewed_artifacts = [
            {"artifactId": item.artifact_id, "contentHash": item.content_hash, "producerAgent": item.producer}
            for item in context.upstream
        ]
        review_identity = {
            "reviewedArtifactId": reviewed.artifact_id if reviewed else "",
            "reviewedContentHash": reviewed.content_hash if reviewed else "",
            "producerAgent": reviewed.producer if reviewed else "unknown",
            "criticAgent": "critic",
            "reviewedArtifacts": reviewed_artifacts,
        }
        duplicate = next(
            (item for item in context.upstream if item.artifact_type == ArtifactType.DUP_REPORT),
            None,
        )
        if duplicate and duplicate.content.get("isExactDuplicate") is True:
            confidence = float(duplicate.content.get("confidence", 0))
            threshold = float(duplicate.content.get("threshold", 0.92))
            candidates = duplicate.content.get("candidates", [])
            duplicate_of = duplicate.content.get("duplicateOf")
            if not duplicate_of and isinstance(candidates, list) and candidates:
                candidate = candidates[0]
                duplicate_of = candidate.get("issueNumber") if isinstance(candidate, dict) else None
            if confidence >= threshold and isinstance(duplicate_of, int) and duplicate_of > 0:
                review_identity.update({
                    "approvedAction": "duplicate_close",
                    "duplicateOf": duplicate_of,
                    "duplicateConfidence": confidence,
                })
        if failed:
            return {**base, **review_identity, "verdict": "revise", "notes": ["deterministic gate failed"], "independent": True}
        if unanswered:
            return {**base, **review_identity, "verdict": "blocked", "notes": [f"human decision required: {item}" for item in unanswered], "independent": True}
        return {**base, **review_identity, "verdict": "pass", "notes": context.revision_notes, "independent": True}
    if output == ArtifactType.WRITEBACK_INTENT:
        critic = next((item for item in context.upstream if item.artifact_type == ArtifactType.CRITIC_VERDICT), None)
        if not critic or critic.content.get("verdict") != "pass":
            return {**base, "authorized": False, "action": "escalate", "reason": "critic did not pass", "credentialFree": True}
        action = "private_security_report" if task.mode.value == "security_audit" else "branch_pr"
        if task.task_type.value == "remediate":
            action = "private_security_pr"
        if task.task_type.value in {"classify", "label", "intake", "dedupe", "respond", "clarify"}:
            action = "issue_update"
        if task.task_type.value == "dedupe" and critic.content.get("approvedAction") == "duplicate_close":
            action = "duplicate_close"
        if task.task_type.value == "label":
            action = "labels_set"
        if task.task_type.value == "review":
            action = "review_comment"
        if task.task_type.value == "escalate":
            action = "escalate"
        if task.task_type.value == "release":
            action = "draft_release"
        authorized = action != "escalate"
        return {**base, "authorized": authorized, "action": action, "credentialFree": True,
                "publishRelease": False, "deploy": False, "idempotencyKey": f"{task.task_id}:{action}",
                "reviewedArtifacts": critic.content.get("reviewedArtifacts", []),
                "issueNumber": task.metadata.get("issueNumber"),
                "pullNumber": task.metadata.get("pullNumber"),
                "duplicateOf": critic.content.get("duplicateOf"),
                "confidence": critic.content.get("duplicateConfidence")}
    return {**base, "status": "complete"}
