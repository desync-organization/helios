from fastapi import APIRouter


def router(runtime) -> APIRouter:
    result = APIRouter()

    @result.get("/roles")
    async def roles() -> dict:
        return {"roles": sorted(runtime.experts)}

    return result

