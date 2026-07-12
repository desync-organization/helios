import importlib

from fastapi import APIRouter, HTTPException


def router() -> APIRouter:
    result = APIRouter()

    @result.post("/evals/run")
    async def run_eval(payload: dict) -> dict:
        try:
            evaluator = importlib.import_module("helios_member3_evals")
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="Member 3 evaluator is not installed") from exc
        return await evaluator.run(payload)

    return result

