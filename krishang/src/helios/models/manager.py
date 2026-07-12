from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from helios.clock import now_utc

from .registry import ModelDefinition


class ModelEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    role: str
    model_id: str
    run_id: str | None = None
    timestamp: datetime = Field(default_factory=now_utc)


class ModelManager:
    def __init__(self, registry: dict[str, ModelDefinition], max_vram_mb: int) -> None:
        self.registry = registry
        self.max_vram_mb = max_vram_mb
        self.loaded: dict[str, ModelDefinition] = {}
        self.events: list[ModelEvent] = []
        self._last_used: dict[str, int] = {}
        self._clock = 0

    async def acquire(self, role: str, run_id: str | None = None) -> ModelDefinition:
        definition = self.registry[role]
        self._clock += 1
        if role in self.loaded:
            self._last_used[role] = self._clock
            self.events.append(ModelEvent(type="model_warm_reuse", role=role, model_id=definition.model_id, run_id=run_id))
            return definition
        while self._used_vram() + definition.estimated_vram_mb > self.max_vram_mb:
            candidates = [item for item in self.loaded if not self.loaded[item].hot]
            if not candidates:
                raise MemoryError(f"model {role} does not fit within the configured VRAM budget")
            evicted_role = min(candidates, key=lambda item: self._last_used[item])
            evicted = self.loaded.pop(evicted_role)
            self._last_used.pop(evicted_role, None)
            self.events.append(ModelEvent(type="model_evicted", role=evicted_role, model_id=evicted.model_id, run_id=run_id))
        self.loaded[role] = definition
        self._last_used[role] = self._clock
        self.events.append(ModelEvent(type="model_loaded", role=role, model_id=definition.model_id, run_id=run_id))
        return definition

    def _used_vram(self) -> int:
        return sum(item.estimated_vram_mb for item in self.loaded.values())
