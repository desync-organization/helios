from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field

from helios.clock import now_utc

from .client import LlamaClient
from .registry import ModelDefinition


class ModelEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    role: str
    model_id: str
    run_id: str | None = None
    timestamp: datetime = Field(default_factory=now_utc)


class ModelManager:
    def __init__(
        self,
        registry: dict[str, ModelDefinition],
        max_vram_mb: int,
        *,
        probe_transport: httpx.AsyncBaseTransport | None = None,
        probe_timeout: float = 2.0,
    ) -> None:
        self.registry = registry
        self.max_vram_mb = max_vram_mb
        self.loaded: dict[str, ModelDefinition] = {}
        self.events: list[ModelEvent] = []
        self._last_used: dict[str, int] = {}
        self._clock = 0
        self._probe_transport = probe_transport
        self._probe_timeout = probe_timeout

    async def acquire(self, role: str, run_id: str | None = None) -> ModelDefinition:
        definition = self.registry[role]
        await self._verify_identity(definition)
        self._clock += 1
        if role in self.loaded:
            self._last_used[role] = self._clock
            self.events.append(
                ModelEvent(
                    type="model_warm_reuse",
                    role=role,
                    model_id=definition.model_id,
                    run_id=run_id,
                )
            )
            return definition
        shared_roles = [
            loaded_role
            for loaded_role, loaded_definition in self.loaded.items()
            if loaded_definition.physical_key == definition.physical_key
        ]
        if shared_roles:
            self.loaded[role] = definition
            self._last_used[role] = self._clock
            for shared_role in shared_roles:
                self._last_used[shared_role] = self._clock
            self.events.append(
                ModelEvent(
                    type="model_shared_reuse",
                    role=role,
                    model_id=definition.model_id,
                    run_id=run_id,
                )
            )
            return definition
        while self._used_vram() + definition.estimated_vram_mb > self.max_vram_mb:
            candidates = self._evictable_allocations()
            if not candidates:
                raise MemoryError(
                    f"model {role} does not fit within the configured VRAM budget"
                )
            evicted_key = min(
                candidates,
                key=lambda key: min(self._last_used[item] for item in candidates[key]),
            )
            evicted_roles = candidates[evicted_key]
            evicted = self.loaded[evicted_roles[0]]
            for evicted_role in evicted_roles:
                self.loaded.pop(evicted_role)
                self._last_used.pop(evicted_role, None)
            self.events.append(
                ModelEvent(
                    type="model_evicted",
                    role=evicted_roles[0],
                    model_id=evicted.model_id,
                    run_id=run_id,
                )
            )
        self.loaded[role] = definition
        self._last_used[role] = self._clock
        self.events.append(
            ModelEvent(
                type="model_loaded",
                role=role,
                model_id=definition.model_id,
                run_id=run_id,
            )
        )
        return definition

    async def _verify_identity(self, definition: ModelDefinition) -> None:
        if not definition.verify_identity:
            return
        if not definition.expected_server_id:
            raise RuntimeError(
                f"model {definition.role} requires identity verification without an expected ID"
            )
        status = await LlamaClient(
            definition.endpoint,
            timeout=self._probe_timeout,
            expected_model_id=definition.expected_server_id,
            transport=self._probe_transport,
        ).probe()
        if not status.ready:
            raise ConnectionError(
                f"model endpoint identity verification failed for {definition.role}: "
                f"{status.error}"
            )

    def _used_vram(self) -> int:
        allocations: dict[tuple[str, str], ModelDefinition] = {}
        for definition in self.loaded.values():
            allocations.setdefault(definition.physical_key, definition)
        return sum(item.estimated_vram_mb for item in allocations.values())

    def _evictable_allocations(self) -> dict[tuple[str, str], list[str]]:
        allocations: dict[tuple[str, str], list[str]] = {}
        for role, definition in self.loaded.items():
            allocations.setdefault(definition.physical_key, []).append(role)
        return {
            key: roles
            for key, roles in allocations.items()
            if not any(self.loaded[role].hot for role in roles)
        }
