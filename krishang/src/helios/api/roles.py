from fastapi import APIRouter


def router(runtime) -> APIRouter:
    result = APIRouter()

    @result.get("/roles")
    async def roles() -> dict:
        return {"schemaVersion": "1.0", "roles": runtime.reservoir.planner_catalog()}

    return result
