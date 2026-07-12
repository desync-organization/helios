from fastapi import APIRouter

from helios.models.bootstrap import preflight


def router(runtime) -> APIRouter:
    result = APIRouter()

    @result.get("/health/live")
    async def live() -> dict:
        return {"live": True}

    @result.get("/health/ready")
    async def ready() -> dict:
        value = preflight(runtime.settings)
        return {**value, "runtime": runtime.state()}

    @result.get("/state")
    async def state() -> dict:
        return runtime.state()

    return result

