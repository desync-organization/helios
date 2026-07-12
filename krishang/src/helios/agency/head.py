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
        if node.output_artifact == ArtifactType.TEST_RESULT.value and content.get("success") is not True:
            raise HeadValidationError("test agent did not produce an authoritative passing result")
        if node.output_artifact == ArtifactType.SECURITY_REPORT.value and content.get("safe") is not True:
            raise HeadValidationError("security agent did not clear the artifact")
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
            reviewed = next((item for item in upstream if item.artifact_id == content.get("reviewedArtifactId")), None)
            if (not reviewed or reviewed.content_hash != content.get("reviewedContentHash")
                    or content.get("producerAgent") == content.get("criticAgent")):
                raise HeadValidationError("critic identity or reviewed artifact proof is invalid")
            producer_adapter = reviewed.content.get("modelProvenance", {}).get("adapterId")
            critic_adapter = content.get("modelProvenance", {}).get("adapterId")
            if producer_adapter and producer_adapter == critic_adapter:
                raise HeadValidationError("critic cannot use the producer's adapter")
            checks.extend(["independent-critic-verdict", "critic-reviewed-content-hash"])
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
