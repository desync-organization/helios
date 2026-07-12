"""Secret and PII detection that never returns raw matched values."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

SCANNER_VERSION = "1.0.0"

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
)


@dataclass(frozen=True, slots=True)
class Finding:
    kind: str
    fingerprint: str
    start: int
    end: int


def _fingerprint(kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{kind}\0{value}".encode()).hexdigest()[:16]
    return f"{kind}:{digest}"


def scan_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                Finding(
                    kind=kind,
                    fingerprint=_fingerprint(kind, match.group(0)),
                    start=match.start(),
                    end=match.end(),
                )
            )
    return sorted(findings, key=lambda item: (item.start, item.end, item.kind))


def redact_text(text: str) -> tuple[str, list[Finding]]:
    findings = scan_text(text)
    redacted = text
    for finding in reversed(findings):
        marker = f"[REDACTED:{finding.kind.upper()}:{finding.fingerprint.split(':')[1]}]"
        redacted = redacted[: finding.start] + marker + redacted[finding.end :]
    return redacted, findings


def scan_value(value: Any) -> list[Finding]:
    if isinstance(value, str):
        return scan_text(value)
    if isinstance(value, dict):
        return [finding for item in value.values() for finding in scan_value(item)]
    if isinstance(value, list):
        return [finding for item in value for finding in scan_value(item)]
    return []
