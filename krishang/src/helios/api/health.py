import asyncio

from fastapi import APIRouter

from helios.models.bootstrap import runtime_preflight


def router(runtime) -> APIRouter:
    result = APIRouter()

    @result.get("/health/live")
    async def live() -> dict:
        return {"live": True}

    @result.get("/health/ready")
    async def ready() -> dict:
        value = await runtime_preflight(
            runtime.settings,
            runtime.model_manager.registry,
        )
        try:
            controls = await asyncio.wait_for(runtime.control_plane.get_control_state(), timeout=2)
        except Exception as exc:
            value["ready"] = False
            value.setdefault("checks", {})["controlPlane"] = False
            value["controlPlaneError"] = type(exc).__name__
        else:
            value.setdefault("checks", {})["controlPlane"] = True
            value["acceptingWork"] = not (
                runtime.paused or controls.global_paused or controls.emergency_mode
            )
        return {**value, "runtime": runtime.state()}

    @result.get("/state")
    async def state() -> dict:
        return runtime.state()

    return result
