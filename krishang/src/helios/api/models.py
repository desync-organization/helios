from fastapi import APIRouter

from helios.models.bootstrap import runtime_preflight
from helios.models.vram import memory_snapshot


def router(runtime) -> APIRouter:
    result = APIRouter()

    @result.get("/models")
    async def models() -> dict:
        return {
            "loaded": [
                item.model_dump(mode="json")
                for item in runtime.model_manager.loaded.values()
            ],
            "telemetry": [
                item.model_dump(mode="json") for item in runtime.model_manager.events
            ],
            "memory": memory_snapshot(),
        }

    @result.get("/preflight")
    async def model_preflight() -> dict:
        return await runtime_preflight(
            runtime.settings,
            runtime.model_manager.registry,
        )

    return result
