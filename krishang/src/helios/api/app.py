from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import mutation_guard
from .evals import router as evals_router
from .health import router as health_router
from .models import router as models_router
from .roles import router as roles_router


def create_app(runtime) -> FastAPI:
    app = FastAPI(title="Helios Runtime", version="1.0")
    app.add_middleware(CORSMiddleware, allow_origins=[runtime.settings.helios_allowed_origin],
                       allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    app.include_router(health_router(runtime))
    app.include_router(models_router(runtime))
    app.include_router(roles_router(runtime))
    app.include_router(evals_router())
    guard = mutation_guard(runtime.settings.helios_local_api_token)

    @app.post("/control/pause", dependencies=[Depends(guard)])
    async def pause() -> dict:
        runtime.paused = True
        return runtime.state()

    @app.post("/control/resume", dependencies=[Depends(guard)])
    async def resume() -> dict:
        runtime.paused = False
        return runtime.state()

    @app.post("/reload", dependencies=[Depends(guard)])
    async def reload_safe_configuration() -> dict:
        try:
            reservoir = runtime.reload_reservoir()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"reloaded": True, "scope": ["roles", "model-readiness"],
                "reservoir": reservoir, "state": runtime.state()}

    return app
