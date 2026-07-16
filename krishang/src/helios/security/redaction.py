import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([^\s'\"]+)"),
    re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}", re.I),
    re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.I | re.S),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
]

SUSPECTED_SECRET_PATTERNS = [
    re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}", re.I),
    re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.I | re.S),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{32,}"),
]

SENSITIVE_KEYS = {
    "apikey",
    "authorization",
    "cookie",
    "credentials",
    "githubappprivatekey",
    "leaseToken".lower(),
    "password",
    "privatekey",
    "proxyToken".lower(),
    "rawsecret",
    "secret",
    "setcookie",
    "token",
}


def _sensitive_key(value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(value).lower())
    return normalized in SENSITIVE_KEYS or normalized.endswith(("password", "privatekey", "secret", "token"))


def redact_text(value: str) -> str:
    result = value
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]" if match.lastindex and match.lastindex > 1 else "[REDACTED]", result)
    result = re.sub(r"[A-Za-z]:\\[^\s]+|/(?:home|Users)/[^\s]+", "[LOCAL_PATH]", result)
    return result


def contains_suspected_secret(value: str) -> bool:
    """Detect high-confidence credential material without rewriting source code."""

    return any(pattern.search(value) for pattern in SUSPECTED_SECRET_PATTERNS)


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
