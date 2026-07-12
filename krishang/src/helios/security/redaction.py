import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([^\s'\"]+)"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def redact_text(value: str) -> str:
    result = value
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]" if match.lastindex and match.lastindex > 1 else "[REDACTED]", result)
    result = re.sub(r"[A-Za-z]:\\[^\s]+|/(?:home|Users)/[^\s]+", "[LOCAL_PATH]", result)
    return result


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): redact(item) for key, item in value.items() if str(key).lower() not in {"raw_secret", "private_key"}}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value

