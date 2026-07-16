from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from helios.site_generation import (
    SiteGenerationError,
    SiteGenerationReadiness,
    SiteGenerator,
    SitePromptRequest,
    StaticSiteResult,
)


class WebSocketPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    type: Literal["prompt"]
    data: str = Field(min_length=1, max_length=8_000)


def router(generator: SiteGenerator, *, allowed_origin: str) -> APIRouter:
    result = APIRouter()

    @result.get("/health/site", response_model=SiteGenerationReadiness)
    async def site_readiness() -> SiteGenerationReadiness:
        return await generator.readiness()

    @result.post("/generate/site", response_model=StaticSiteResult)
    async def generate_site(request: SitePromptRequest) -> StaticSiteResult:
        try:
            return await generator.generate(request)
        except SiteGenerationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Local site generation failed") from exc

    @result.websocket("/ws")
    async def generate_site_websocket(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin and origin.rstrip("/") != allowed_origin.rstrip("/"):
            await websocket.close(code=1008, reason="WebSocket origin is not allowed")
            return
        await websocket.accept()
        while True:
            try:
                payload: Any = await websocket.receive_json()
            except WebSocketDisconnect:
                return
            except ValueError:
                await websocket.send_json({
                    "type": "error",
                    "data": "Message must be valid JSON with type 'prompt' and text data.",
                })
                continue
            try:
                message = WebSocketPrompt.model_validate(payload)
                request = SitePromptRequest(prompt=message.data)
            except ValidationError:
                await websocket.send_json({
                    "type": "error",
                    "data": "Expected a non-empty {type: 'prompt', data: text} message.",
                })
                continue

            await websocket.send_json({
                "type": "progress",
                "data": f"HELIOS — Interpreting the site request locally with {generator.model}.",
            })
            try:
                generated = await generator.generate(request)
            except SiteGenerationError as exc:
                await websocket.send_json({"type": "error", "data": str(exc)})
                continue
            except Exception:
                await websocket.send_json({"type": "error", "data": "Local site generation failed."})
                continue

            await websocket.send_json({
                "type": "progress",
                "data": "HELIOS — Compiled and validated three accessible static site files.",
            })
            for file in generated.files:
                artifact = {
                    "id": f"site-{file.path}",
                    "filename": file.path,
                    "path": file.path,
                    "language": _language(file.path),
                    "code": file.content,
                    "artifactType": "static-site-file",
                    "progress": 100,
                }
                await websocket.send_json({"type": "artifact", "data": artifact, **artifact})
            await websocket.send_json({
                "type": "complete",
                "data": "Your Helios static site is ready.",
                "files": [file.path for file in generated.files],
                "model": generated.model,
                "promptHash": generated.prompt_hash,
            })

    return result


def _language(path: str) -> str:
    return {"index.html": "html", "styles.css": "css", "app.js": "javascript"}[path]
