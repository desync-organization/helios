"""Environment-backed gateway configuration with safe defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    control_plane_url: str | None
    upstream_token: str | None
    client_token: str | None
    allow_readonly_demo: bool
    max_message_bytes: int = 16_384
    max_prompt_chars: int = 8_192
    requests_per_minute: int = 12
    dedupe_ttl_seconds: int = 300
    buffer_size: int = 512
    heartbeat_seconds: float = 15.0
    upstream_poll_seconds: float = 0.5

    @classmethod
    def from_environment(cls) -> GatewayConfig:
        return cls(
            control_plane_url=os.getenv("HERMES_CONTROL_PLANE_URL"),
            upstream_token=os.getenv("HERMES_GATEWAY_UPSTREAM_TOKEN"),
            client_token=os.getenv("HERMES_GATEWAY_CLIENT_TOKEN"),
            allow_readonly_demo=_bool("HERMES_ALLOW_READONLY_DEMO"),
        )

