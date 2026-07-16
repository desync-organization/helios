from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from helios.evals.member3 import run_member3_evaluation


def router(guard: Callable) -> APIRouter:
    result = APIRouter(dependencies=[Depends(guard)])

    @result.post("/evals/run")
    async def run_eval(payload: dict) -> dict:
        try:
            return await run_member3_evaluation(payload)
        except ImportError as exc:
            raise HTTPException(
                status_code=503,
                detail="Member 3 evaluator is not installed or is incompatible",
            ) from exc
        except (ValidationError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail="invalid evaluation payload or result contract",
            ) from exc

    return result
