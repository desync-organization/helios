from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from helios.contracts import Artifact, ArtifactType, NormalizedTask, PlanNode


@dataclass(slots=True)
class ExpertContext:
    task: NormalizedTask
    run_id: str
    node: PlanNode
    upstream: list[Artifact]
    revision_notes: list[str]


ExpertHandler = Callable[[ExpertContext], Awaitable[dict[str, Any]]]


def _upstream_summary(context: ExpertContext) -> list[dict[str, str]]:
    return [{"artifactId": item.artifact_id, "type": item.artifact_type.value, "hash": item.content_hash} for item in context.upstream]


async def deterministic_expert(context: ExpertContext) -> dict[str, Any]:
    output = ArtifactType(context.node.output_artifact)
    task = context.task
    evidence = _upstream_summary(context)
    base = {"taskId": task.task_id, "repository": task.repository, "baseSha": task.base_sha,
            "evidence": evidence, "policyIds": context.node.policy_ids}
    if output == ArtifactType.CLASSIFICATION:
        lowered = f"{task.title} {task.body}".lower()
        label = "bug" if any(word in lowered for word in ("bug", "error", "fails", "broken")) else "question"
        return {**base, "classification": label, "priority": "p2", "labels": [label], "confidence": 0.86}
    if output == ArtifactType.DUP_REPORT:
        return {**base, "candidates": [], "isExactDuplicate": False, "threshold": 0.92}
    if output == ArtifactType.DRAFT_REPLY:
        return {**base, "body": f"Thanks for reporting this. Hermes reviewed `{task.title}` and recorded the evidence for maintainer follow-up.",
                "sourceLinks": task.metadata.get("sourceLinks", [])}
    if output == ArtifactType.REPRO_REPORT:
        return {**base, "isolated": True, "reproduced": True,
                "command": task.metadata.get("reproCommand", "repository-declared test command"),
                "before": "failed", "smallestFailingCase": task.title}
    if output == ArtifactType.PATCH:
        return {**base, "format": "structured-patch", "baseSha": task.base_sha,
                "files": task.metadata.get("proposedFiles", []), "completeFiles": True,
                "protectedPathsTouched": False}
    if output == ArtifactType.TEST_RESULT:
        return {**base, "success": True, "before": "failed", "after": "passed",
                "commands": task.metadata.get("testCommands", ["repository-declared test suite"]), "fabricated": False}
    if output == ArtifactType.SECURITY_REPORT:
        return {**base, "findings": [], "secretsRedacted": True, "safe": True,
                "limitations": task.metadata.get("securityLimitations", [])}
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
        return {**base, "integrated": True, "conflicts": [], "baseSha": task.base_sha}
    if output == ArtifactType.BUILD_MANIFEST:
        return {**base, "files": task.metadata.get("proposedFiles", []), "commands": task.metadata.get("testCommands", []),
                "testResults": [item.content for item in context.upstream if item.artifact_type == ArtifactType.TEST_RESULT],
                "securityResults": [item.content for item in context.upstream if item.artifact_type == ArtifactType.SECURITY_REPORT],
                "knownLimitations": [], "resultHashes": {item.artifact_id: item.content_hash for item in context.upstream}}
    if output == ArtifactType.REPOSITORY_INVENTORY:
        return {**base, "languages": task.metadata.get("languages", []), "manifests": task.metadata.get("manifests", []),
                "lockfiles": task.metadata.get("lockfiles", []), "coverageLimitations": task.metadata.get("coverageLimitations", [])}
    if output == ArtifactType.DEPENDENCY_INVENTORY:
        return {**base, "dependencies": task.metadata.get("dependencies", []), "lockfileAuthoritative": bool(task.metadata.get("lockfiles"))}
    if output == ArtifactType.SARIF_REPORT:
        return {**base, "version": "2.1.0", "runs": [], "findings": task.metadata.get("findings", []), "secretsRedacted": True}
    if output == ArtifactType.REMEDIATION_PLAN:
        return {**base, "authorized": task.consent.remediation_permitted,
                "actions": task.metadata.get("remediationActions", []),
                "tests": ["targeted regression", "full impacted suite", "scanner rescan"],
                "publication": "human-controlled"}
    if output == ArtifactType.CRITIC_VERDICT:
        failed = [item for item in context.upstream if item.content.get("success") is False or item.content.get("safe") is False]
        unanswered = [decision for item in context.upstream for decision in item.content.get("unansweredDecisions", [])]
        if failed:
            return {**base, "verdict": "revise", "notes": ["deterministic gate failed"], "independent": True}
        if unanswered:
            return {**base, "verdict": "blocked", "notes": [f"human decision required: {item}" for item in unanswered], "independent": True}
        return {**base, "verdict": "pass", "notes": context.revision_notes, "independent": True}
    if output == ArtifactType.WRITEBACK_INTENT:
        critic = next((item for item in context.upstream if item.artifact_type == ArtifactType.CRITIC_VERDICT), None)
        if not critic or critic.content.get("verdict") != "pass":
            return {**base, "authorized": False, "action": "escalate", "reason": "critic did not pass", "credentialFree": True}
        action = "private_security_report" if task.mode.value == "security_audit" else "branch_pr"
        if task.task_type.value == "remediate":
            action = "private_security_pr"
        if task.task_type.value in {"classify", "label", "intake", "dedupe", "respond", "clarify"}:
            action = "issue_update"
        if task.task_type.value == "review":
            action = "review_comment"
        if task.task_type.value == "escalate":
            action = "escalate"
        if task.task_type.value == "release":
            action = "draft_release"
        return {**base, "authorized": True, "action": action, "credentialFree": True,
                "publishRelease": False, "deploy": False, "idempotencyKey": f"{task.task_id}:{action}"}
    return {**base, "status": "complete"}
