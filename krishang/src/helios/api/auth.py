from fastapi import Header, HTTPException


def mutation_guard(expected_token: str):
    async def guard(authorization: str = Header(default="")) -> None:
        if not expected_token or authorization != f"Bearer {expected_token}":
            raise HTTPException(status_code=401, detail="valid local API token required")
    return guard

