"""Authentication and recursive outbound redaction."""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

_SENSITIVE_KEYS = re.compile(
    r"(?:token|secret|authorization|cookie|private.?key|raw.?body|provider.?key)",
    re.IGNORECASE,
)
_SECRET_VALUES = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def authenticated(supplied: str | None, expected: str | None) -> bool:
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SENSITIVE_KEYS.search(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in _SECRET_VALUES:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    return value
