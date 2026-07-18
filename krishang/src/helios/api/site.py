from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from helios.site_generation import (
    SiteAgentMessage,
    SiteGenerationError,
    SiteGenerationProgress,
    SiteGenerationReadiness,
    SiteGenerator,
    SiteMessageReporter,
    SitePromptRequest,
    StaticSiteResult,
)


SITE_PLAN_NODES = [
    {
        "id": "plan",
        "label": "Decompose task",
        "role": "Head local LLM",
        "detail": "Waiting for a site request.",
        "dependencies": [],
        "artifacts": ["Typed three-specialist plan"],
    },
    {
        "id": "html",
        "label": "Author HTML",
        "role": "HTML SLM",
        "detail": "Waiting for the head plan.",
        "dependencies": ["plan"],
        "artifacts": ["index.html"],
    },
    {
        "id": "css",
        "label": "Author CSS",
        "role": "CSS SLM",
        "detail": "Waiting for the validated HTML contract.",
        "dependencies": ["html"],
        "artifacts": ["styles.css"],
    },
    {
        "id": "javascript",
        "label": "Author JavaScript",
        "role": "JavaScript SLM",
        "detail": "Waiting for the validated HTML contract.",
        "dependencies": ["html"],
        "artifacts": ["app.js"],
    },
    {
        "id": "integrate",
        "label": "Integrate files",
        "role": "Deterministic runtime",
        "detail": "Waiting for all specialist files.",
        "dependencies": ["css", "javascript"],
        "artifacts": ["Integrated static site"],
    },
    {
        "id": "review",
        "label": "Review codebase",
        "role": "Head local LLM",
        "detail": "Waiting for deterministic integration.",
        "dependencies": ["integrate"],
        "artifacts": ["Routed review verdict"],
    },
    {
        "id": "revise",
        "label": "Apply routed revisions",
        "role": "Relevant SLMs",
        "detail": "Waiting for the head review.",
        "dependencies": ["review"],
        "artifacts": ["Revised specialist files"],
    },
    {
        "id": "validate",
        "label": "Validate output",
        "role": "Safety and accessibility checks",
        "detail": "Waiting for review and any routed revision.",
        "dependencies": ["revise"],
        "artifacts": ["HTML, CSS, JavaScript, and provenance checks"],
    },
    {
        "id": "deliver",
        "label": "Stream artifacts",
        "role": "Runtime bridge",
        "detail": "Waiting for validated output.",
        "dependencies": ["validate"],
        "artifacts": [],
    },
]


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

            plan_id = f"site-{uuid4().hex[:12]}"
            active_node_id = "plan"
            await websocket.send_json({
                "type": "plan",
                "data": {
                    "id": plan_id,
                    "title": "Generate static site",
                    "status": "running",
                    "model": generator.model,
                    "nodes": [
                        {**node, "status": "pending", "progress": 0}
                        for node in SITE_PLAN_NODES
                    ],
                },
            })
            await websocket.send_json({
                "type": "progress",
                "data": f"HELIOS — Head {generator.model} is decomposing the task for three SLMs.",
            })

            async def report_progress(update: SiteGenerationProgress) -> None:
                nonlocal active_node_id
                active_node_id = update.stage
                await websocket.send_json({
                    "type": "plan_node_status",
                    "data": {
                        "planId": plan_id,
                        "nodeId": update.stage,
                        "status": update.status,
                        "detail": update.detail,
                        "progress": 100 if update.status == "completed" else 10,
                    },
                })

            async def report_message(message: SiteAgentMessage) -> None:
                message_data = message.model_dump(mode="json", by_alias=True)
                await websocket.send_json({
                    "type": "agent_message",
                    "data": {"planId": plan_id, **message_data},
                })
                sender_label = message.sender.removesuffix("-slm").upper()
                await websocket.send_json({
                    "type": "progress",
                    "data": f"[{sender_label}] {message.tag} — {message.body}",
                })

            message_reporter: SiteMessageReporter = report_message

            try:
                generated = await generator.generate(
                    request,
                    on_progress=report_progress,
                    on_message=message_reporter,
                )
            except SiteGenerationError as exc:
                await _send_plan_failure(websocket, plan_id, active_node_id)
                await websocket.send_json({"type": "error", "data": str(exc)})
                continue
            except Exception:
                await _send_plan_failure(websocket, plan_id, active_node_id)
                await websocket.send_json({"type": "error", "data": "Local site generation failed."})
                continue

            active_node_id = "deliver"
            await websocket.send_json({
                "type": "plan_node_status",
                "data": {
                    "planId": plan_id,
                    "nodeId": "deliver",
                    "status": "running",
                    "detail": "Streaming validated files to the workspace.",
                    "progress": 0,
                },
            })
            await websocket.send_json({
                "type": "progress",
                "data": "HELIOS — Three SLM-authored files passed head review and deterministic validation.",
            })
            delivered_files: list[str] = []
            for index, file in enumerate(generated.files, start=1):
                artifact = {
                    "id": f"site-{file.path}",
                    "filename": file.path,
                    "path": file.path,
                    "language": _language(file.path),
                    "code": file.content,
                    "artifactType": "static-site-file",
                    "progress": 100,
                    "provenance": file.provenance.model_dump(
                        mode="json",
                        by_alias=True,
                    ) if file.provenance else None,
                }
                await websocket.send_json({"type": "artifact", "data": artifact, **artifact})
                delivered_files.append(file.path)
                await websocket.send_json({
                    "type": "plan_node_status",
                    "data": {
                        "planId": plan_id,
                        "nodeId": "deliver",
                        "status": "running",
                        "detail": f"Streamed {index} of {len(generated.files)} files.",
                        "progress": round(index / len(generated.files) * 100),
                        "artifacts": delivered_files,
                    },
                })
            await websocket.send_json({
                "type": "plan_node_status",
                "data": {
                    "planId": plan_id,
                    "nodeId": "deliver",
                    "status": "completed",
                    "detail": "All validated files are available in the workspace.",
                    "progress": 100,
                    "artifacts": delivered_files,
                },
            })
            await websocket.send_json({
                "type": "plan_status",
                "data": {"planId": plan_id, "status": "completed"},
            })
            await websocket.send_json({
                "type": "complete",
                "data": "Your Helios static site is ready.",
                "files": [file.path for file in generated.files],
                "model": generated.model,
                "promptHash": generated.prompt_hash,
                "headReview": generated.head_review.model_dump(
                    mode="json",
                    by_alias=True,
                ) if generated.head_review else None,
                "modelInvocations": [
                    item.model_dump(mode="json", by_alias=True)
                    for item in generated.model_invocations
                ],
                "agentMessages": [
                    item.model_dump(mode="json", by_alias=True)
                    for item in generated.agent_messages
                ],
            })

    return result


async def _send_plan_failure(
    websocket: WebSocket,
    plan_id: str,
    node_id: str,
) -> None:
    await websocket.send_json({
        "type": "plan_node_status",
        "data": {
            "planId": plan_id,
            "nodeId": node_id,
            "status": "failed",
            "detail": "This execution stage failed. See the event log for the reported error.",
        },
    })
    await websocket.send_json({
        "type": "plan_status",
        "data": {"planId": plan_id, "status": "failed"},
    })


def _language(path: str) -> str:
    return {"index.html": "html", "styles.css": "css", "app.js": "javascript"}[path]
