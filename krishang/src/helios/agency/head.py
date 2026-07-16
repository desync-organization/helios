import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any

from helios.contracts import Artifact, ArtifactType
from helios.contracts.plan import PlanNode


class HeadValidationError(ValueError):
    pass


@dataclass(slots=True)
class HeadValidationResult:
    valid: bool
    checks: list[str]
    summary: dict[str, Any]


class _SafeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "script":
            self.errors.append("script elements are not allowed")
        for name, value in attrs:
            lowered_name = name.lower()
            lowered_value = (value or "").strip().lower()
            if lowered_name.startswith("on"):
                self.errors.append(f"inline event handler is not allowed: {name}")
            if lowered_value.startswith("javascript:"):
                self.errors.append("javascript URLs are not allowed")


class HeadOrchestratorValidator:
    """Deterministic validation performed before an expert artifact enters the workspace."""

    def validate(self, node: PlanNode, content: dict[str, Any],
                 upstream: list[Artifact] | None = None) -> HeadValidationResult:
        checks = ["output-is-object", "acceptance-criteria-present"]
        if not isinstance(content, dict) or not node.acceptance_criteria:
            raise HeadValidationError("agent output does not satisfy the typed handoff contract")
        if node.output_artifact == ArtifactType.TEST_RESULT.value:
            if (content.get("authoritative") is not True or content.get("fabricated") is not False
                    or not isinstance(content.get("results"), list)
                    or content.get("status") not in {"passed", "failed", "not_configured"}):
                raise HeadValidationError("test agent did not produce authoritative command evidence")
            for result in content["results"]:
                if not isinstance(result, dict) or not result.get("commandHash") or "exitCode" not in result:
                    raise HeadValidationError("test evidence is missing a command hash or exit code")
            checks.append("authoritative-test-evidence")
        if node.output_artifact == ArtifactType.SECURITY_REPORT.value:
            if (content.get("authoritative") is not True or content.get("fabricated") is not False
                    or not isinstance(content.get("scannerResults"), list)
                    or not isinstance(content.get("coverageComplete"), bool)
                    or content.get("secretsRedacted") is not True):
                raise HeadValidationError("security agent did not produce authoritative scanner evidence")
            checks.extend(["authoritative-scanner-evidence", "secret-redaction-declared"])
        if node.output_artifact in {
            ArtifactType.REPOSITORY_INVENTORY.value,
            ArtifactType.DEPENDENCY_INVENTORY.value,
            ArtifactType.SARIF_REPORT.value,
        } and content.get("authoritative") is not True:
            raise HeadValidationError("repository evidence is not authoritative")
        if node.output_artifact == ArtifactType.SARIF_REPORT.value and (
            content.get("fabricated") is not False
            or not isinstance(content.get("coverageComplete"), bool)
            or not isinstance(content.get("scannerResults"), list)
            or content.get("secretsRedacted") is not True
        ):
            raise HeadValidationError("scanner report is missing authoritative execution evidence")
        if node.output_artifact == ArtifactType.PATCH.value:
            if content.get("noChangesRequired") is not True and (
                not isinstance(content.get("files"), list) or not content["files"]
            ):
                raise HeadValidationError("patch does not contain complete files")
        if node.output_artifact == ArtifactType.PACKAGE_RESULT.value and content.get("integrated") is not True:
            raise HeadValidationError("integration contains unresolved file ownership conflicts")
        if node.output_artifact == ArtifactType.BUILD_MANIFEST.value:
            if not isinstance(content.get("resultHashes"), dict) or not content.get("testResults") or not content.get("securityResults"):
                raise HeadValidationError("build manifest is missing test, security, or hash evidence")
            checks.append("complete-build-evidence")
        if node.expert in {"html-slm", "css-slm", "javascript-slm"}:
            files = content.get("files")
            if not isinstance(files, list) or not files:
                raise HeadValidationError(f"{node.expert} must return at least one complete file")
            for item in files:
                if not isinstance(item, dict) or not item.get("path") or not isinstance(item.get("content"), str):
                    raise HeadValidationError(f"{node.expert} returned an invalid file record")
                path = str(item["path"]).replace("\\", "/")
                parsed = PurePosixPath(path)
                expected_extension = {"html-slm": ".html", "css-slm": ".css", "javascript-slm": ".js"}[node.expert]
                if parsed.is_absolute() or ".." in parsed.parts or parsed.suffix.lower() != expected_extension:
                    raise HeadValidationError(f"{node.expert} returned an unsafe or incorrect file path: {path}")
            checks.append("complete-file-records")
            combined = "\n".join(item["content"] for item in files)
            if node.expert == "html-slm":
                lowered = combined.lower()
                if "<html" not in lowered or "</html>" not in lowered or "<script" in lowered:
                    raise HeadValidationError("HTML SLM output must be a complete document without inline scripts")
                parser = _SafeHTMLParser()
                parser.feed(combined)
                if parser.errors:
                    raise HeadValidationError("; ".join(parser.errors))
                checks.extend(["complete-html-document", "no-inline-script"])
            elif node.expert == "css-slm":
                lowered = combined.lower()
                if (combined.count("{") != combined.count("}") or "javascript:" in lowered
                        or "expression(" in lowered or re.search(r"@import\s+url", lowered)):
                    raise HeadValidationError("CSS SLM output has unbalanced rules or unsafe URL content")
                checks.extend(["balanced-css-rules", "safe-css-urls"])
            else:
                if (not self._balanced_javascript(combined)
                        or re.search(r"\b(eval|Function)\s*\(", combined)
                        or re.search(r"\b(fetch|XMLHttpRequest|WebSocket)\s*\(?", combined)):
                    raise HeadValidationError("JavaScript SLM output failed syntax/safety validation")
                checks.extend(["balanced-javascript", "no-dynamic-code-execution"])
        if node.output_artifact == ArtifactType.CRITIC_VERDICT.value:
            if content.get("verdict") not in {"pass", "revise", "blocked"} or content.get("independent") is not True:
                raise HeadValidationError("critic verdict is invalid or not independent")
            upstream = upstream or []
            records = content.get("reviewedArtifacts")
            if records is None and len(upstream) == 1:
                records = [{
                    "artifactId": content.get("reviewedArtifactId"),
                    "contentHash": content.get("reviewedContentHash"),
                    "producerAgent": content.get("producerAgent"),
                }]
            if not isinstance(records, list) or len(records) != len(upstream):
                raise HeadValidationError("critic did not review every direct upstream artifact")
            expected = {
                item.artifact_id: (item.content_hash, item.producer)
                for item in upstream
            }
            actual: dict[str, tuple[str, str]] = {}
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get("artifactId"), str):
                    raise HeadValidationError("critic lineage record is malformed")
                artifact_id = record["artifactId"]
                if artifact_id in actual:
                    raise HeadValidationError("critic lineage contains a duplicate artifact")
                actual[artifact_id] = (str(record.get("contentHash", "")), str(record.get("producerAgent", "")))
            if actual != expected or any(producer == content.get("criticAgent") for _, producer in actual.values()):
                raise HeadValidationError("critic identity or reviewed artifact proof is invalid")
            critic_adapter = content.get("modelProvenance", {}).get("adapterId")
            producer_adapters = {
                item.content.get("modelProvenance", {}).get("adapterId")
                for item in upstream
                if item.content.get("modelProvenance", {}).get("adapterId")
            }
            if critic_adapter and critic_adapter in producer_adapters:
                raise HeadValidationError("critic cannot use the producer's adapter")
            checks.extend(["independent-critic-verdict", "critic-reviewed-all-content-hashes"])
        return HeadValidationResult(valid=True, checks=checks, summary={
            "agent": node.expert, "artifactType": node.output_artifact,
            "acceptanceCriteriaCount": len(node.acceptance_criteria),
        })

    @staticmethod
    def _balanced_javascript(source: str) -> bool:
        pairs = {"{": "}", "[": "]", "(": ")"}
        stack: list[str] = []
        quote: str | None = None
        escaped = False
        for char in source:
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"', "`"}:
                quote = char
            elif char in pairs:
                stack.append(pairs[char])
            elif char in pairs.values() and (not stack or stack.pop() != char):
                return False
        return not stack and quote is None
