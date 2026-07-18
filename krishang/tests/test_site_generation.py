import hashlib
import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from helios.api import create_app
from helios.config import Settings
from helios.control_plane import InMemoryControlPlane
from helios.runtime import HeliosRuntime
from helios.site_generation import (
    OllamaClient,
    SiteAgentMessage,
    SiteFile,
    SiteGenerationProgress,
    SitePromptRequest,
    SiteSpec,
    StaticSiteGenerator,
    StaticSiteResult,
)


SPEC = {
    "project_name": "Common Ground",
    "page_title": "Common Ground Community Studio",
    "tagline": "Make room for better ideas.",
    "description": "A welcoming neighborhood studio for workshops, collaboration, and shared creative practice.",
    "language": "en",
    "layout": "split",
    "palette": {"theme": "light", "primary": "#245c4f", "accent": "#e9a23b"},
    "sections": [
        {
            "heading": "What happens here",
            "body": "Join practical sessions built for curious people at every experience level.",
            "items": ["Hands-on workshops", "Open studio hours", "Community showcases"],
        },
        {
            "heading": "Plan your visit",
            "body": "Find a comfortable pace, clear guidance, and an accessible space near the town center.",
            "items": ["Step-free entrance", "Flexible scheduling"],
        },
    ],
    "cta_label": "Explore the studio",
    "cta_message": "You are now exploring upcoming studio activities.",
}


class FakeSiteClient:
    model = "llama3.2:test"

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or SPEC
        self.calls: list[dict[str, Any]] = []

    async def generate(self, *, prompt: str, json_schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"prompt": prompt, "json_schema": json_schema})
        return self.response


class RepairingSiteClient(FakeSiteClient):
    def __init__(self) -> None:
        super().__init__()
        self.responses = [{**SPEC, "tagline": ""}, SPEC]

    async def generate(self, *, prompt: str, json_schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"prompt": prompt, "json_schema": json_schema})
        return self.responses[len(self.calls) - 1]


def _agent_message(
    sequence: int = 1,
    *,
    message_id: str | None = None,
    sender: str = "html-slm",
    recipient: str = "css-slm",
    tag: str = "@css",
    delivery: str = "direct",
    body: str = "Use the semantic regions and class hooks from the HTML file.",
) -> SiteAgentMessage:
    return SiteAgentMessage(
        schemaVersion="1.0",
        messageId=message_id or f"site-msg-{sequence:04d}",
        sequence=sequence,
        sender=sender,
        recipient=recipient,
        tag=tag,
        kind="handoff",
        phase="html",
        delivery=delivery,
        body=body,
        model="helios-html-slm:test",
        modelDigest="a" * 64,
    )


def _runtime(tmp_path) -> HeliosRuntime:
    settings = Settings(
        environment="test",
        helios_workspace_root=tmp_path / "workspace",
        helios_outbox_path=tmp_path / "workspace" / "outbox.jsonl",
        git_repo_cache_root=tmp_path / "workspace" / "repos",
    )
    return HeliosRuntime(settings, InMemoryControlPlane())


async def test_ollama_client_posts_bounded_structured_request() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"model": "llama3.2:latest", "done": True, "response": json.dumps(SPEC)})

    client = OllamaClient(
        model="llama3.2:latest",
        timeout=30,
        transport=httpx.MockTransport(handler),
    )
    result = await client.generate(prompt="Build a community studio site", json_schema=SiteSpec.model_json_schema())
    readiness = await client.readiness()
    await client.aclose()

    assert result == SPEC
    assert captured["url"] == "http://127.0.0.1:11434/api/generate"
    assert captured["body"]["model"] == "llama3.2:latest"
    assert captured["body"]["stream"] is False
    assert captured["body"]["keep_alive"] == 0
    assert captured["body"]["format"]["additionalProperties"] is False
    assert captured["body"]["options"]["num_predict"] == 640
    assert readiness.ready is True
    assert readiness.error is None


async def test_generator_compiles_prompt_specific_accessible_site() -> None:
    client = FakeSiteClient()
    generator = StaticSiteGenerator(client)
    prompt = "Create a calm community studio site with practical workshops."

    result = await generator.generate(SitePromptRequest(prompt=prompt))

    assert [file.path for file in result.files] == ["index.html", "styles.css", "app.js"]
    assert result.model == "llama3.2:test"
    assert result.prompt_hash == hashlib.sha256(prompt.encode()).hexdigest()
    assert "Common Ground" in result.files[0].content
    assert '<meta name="viewport"' in result.files[0].content
    assert "@media" in result.files[1].content
    assert ":focus-visible" in result.files[1].content
    assert "aria-expanded" in result.files[2].content
    assert len(client.calls) == 1
    assert prompt in client.calls[0]["prompt"]


async def test_generator_reports_the_real_execution_stages() -> None:
    client = FakeSiteClient()
    generator = StaticSiteGenerator(client)
    updates: list[SiteGenerationProgress] = []

    async def capture(update: SiteGenerationProgress) -> None:
        updates.append(update)

    await generator.generate(
        SitePromptRequest(prompt="Build a community studio."),
        on_progress=capture,
    )

    assert [(update.stage, update.status) for update in updates] == [
        ("interpret", "running"),
        ("interpret", "completed"),
        ("compile", "running"),
        ("compile", "completed"),
        ("validate", "running"),
        ("validate", "completed"),
    ]


async def test_generator_repairs_one_invalid_model_specification() -> None:
    client = RepairingSiteClient()
    generator = StaticSiteGenerator(client)

    result = await generator.generate(SitePromptRequest(prompt="Build an accessible community studio."))

    assert result.files[0].path == "index.html"
    assert len(client.calls) == 2
    assert client.calls[0]["json_schema"] is client.calls[1]["json_schema"]
    assert "single allowed schema-repair attempt" in client.calls[1]["prompt"]
    assert "tagline" in client.calls[1]["prompt"]


def test_site_agent_message_validates_canonical_route_and_aliases() -> None:
    message = _agent_message()

    assert message.recipient == "css-slm"
    assert message.tag == "@css"
    assert message.model_dump(mode="json", by_alias=True) == {
        "schemaVersion": "1.0",
        "messageId": "site-msg-0001",
        "sequence": 1,
        "sender": "html-slm",
        "recipient": "css-slm",
        "tag": "@css",
        "kind": "handoff",
        "phase": "html",
        "delivery": "direct",
        "body": "Use the semantic regions and class hooks from the HTML file.",
        "model": "helios-html-slm:test",
        "modelDigest": "a" * 64,
    }

    with pytest.raises(ValidationError, match="tag does not match"):
        _agent_message(recipient="javascript-slm", tag="@css")
    with pytest.raises(ValidationError, match="cannot be sent to the sender"):
        _agent_message(sender="css-slm", recipient="css-slm", tag="@css")
    with pytest.raises(ValidationError, match="delivery does not match"):
        _agent_message(
            recipient="head",
            tag="@head",
            delivery="direct",
        )
    with pytest.raises(ValidationError, match="plain-language notes"):
        _agent_message(body="Replace the stylesheet with .button { color: red; }")


async def test_legacy_generator_accepts_message_reporter_and_defaults_empty_transcript() -> None:
    captured: list[SiteAgentMessage] = []

    async def capture(message: SiteAgentMessage) -> None:
        captured.append(message)

    result = await StaticSiteGenerator(FakeSiteClient()).generate(
        SitePromptRequest(prompt="Build a community studio."),
        on_message=capture,
    )

    assert captured == []
    assert result.agent_messages == []
    assert result.model_dump(mode="json", by_alias=True)["agentMessages"] == []


async def test_site_result_requires_contiguous_message_sequence_and_matching_ids() -> None:
    generated = await StaticSiteGenerator(FakeSiteClient()).generate(
        SitePromptRequest(prompt="Build a community studio."),
    )
    first = _agent_message()
    second = _agent_message(
        2,
        sender="css-slm",
        recipient="javascript-slm",
        tag="@javascript",
    )

    valid = StaticSiteResult(
        model=generated.model,
        prompt_hash=generated.prompt_hash,
        files=generated.files,
        agent_messages=[first, second],
    )
    assert [message.sequence for message in valid.agent_messages] == [1, 2]

    with pytest.raises(ValidationError, match="contiguous and ordered"):
        StaticSiteResult(
            model=generated.model,
            prompt_hash=generated.prompt_hash,
            files=generated.files,
            agent_messages=[second],
        )
    with pytest.raises(ValidationError, match="ID must match"):
        StaticSiteResult(
            model=generated.model,
            prompt_hash=generated.prompt_hash,
            files=generated.files,
            agent_messages=[_agent_message(message_id="site-msg-0002")],
        )


def test_site_result_rejects_missing_or_unsafe_artifacts() -> None:
    with pytest.raises(ValidationError, match="required path"):
        StaticSiteResult(
            model="test",
            prompt_hash="a" * 64,
            files=[
                SiteFile(path="index.html", content="<html></html>"),
                SiteFile(path="index.html", content="<html></html>"),
                SiteFile(path="app.js", content="eval('unsafe')"),
            ],
        )


def test_rest_and_websocket_generation_use_injected_local_client(tmp_path) -> None:
    client = FakeSiteClient()
    app = create_app(_runtime(tmp_path), site_client=client)
    test_client = TestClient(app)

    response = test_client.post("/generate/site", json={"prompt": "Build a community studio."})
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "llama3.2:test"
    assert [file["path"] for file in payload["files"]] == ["index.html", "styles.css", "app.js"]
    assert test_client.get("/health/live").json() == {"live": True}
    assert test_client.get("/health/site").json() == {
        "ready": True,
        "model": "llama3.2:test",
        "provider": "injected",
        "error": None,
        "roles": [],
    }
    assert test_client.post("/generate/site", json={"prompt": "", "extra": True}).status_code == 422

    with test_client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "unknown", "data": "ignored"})
        assert websocket.receive_json()["type"] == "error"

    with pytest.raises(WebSocketDisconnect) as rejected:
        with test_client.websocket_connect(
            "/ws",
            headers={"origin": "https://untrusted.example"},
        ):
            pass
    assert rejected.value.code == 1008
