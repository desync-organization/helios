import hashlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from helios.api import create_app
from helios.config import Settings
from helios.control_plane import InMemoryControlPlane
from helios.runtime import HeliosRuntime
from helios.site_generation import (
    SiteGenerationError,
    SiteGenerationProgress,
    SiteGenerationReadiness,
    SitePromptRequest,
)
from helios.site_orchestration import (
    OrchestratedSiteGenerator,
    SpecialistIdentity,
)


SITE_SPEC = {
    "project_name": "Common Ground",
    "page_title": "Common Ground Studio",
    "tagline": "Make room for better ideas.",
    "description": "A welcoming neighborhood studio for practical creative work.",
    "language": "en",
    "layout": "split",
    "palette": {"theme": "light", "primary": "#245c4f", "accent": "#e9a23b"},
    "sections": [
        {
            "heading": "Workshops",
            "body": "Join practical sessions for every experience level.",
            "items": ["Hands-on sessions"],
        },
        {
            "heading": "Visit",
            "body": "Find a comfortable and accessible place to create.",
            "items": ["Step-free entrance"],
        },
    ],
    "cta_label": "Explore the studio",
    "cta_message": "Upcoming studio activities are ready to explore.",
}

PLAN = {
    "schemaVersion": "1.0",
    "summary": "Create an accessible community studio landing page.",
    "spec": SITE_SPEC,
    "assignments": [
        {
            "owner": "html-slm",
            "path": "index.html",
            "instructions": "Create the semantic document and content structure.",
            "acceptanceCriteria": ["Use one main landmark and one h1."],
        },
        {
            "owner": "css-slm",
            "path": "styles.css",
            "instructions": "Create responsive styling for the supplied document.",
            "acceptanceCriteria": ["Provide visible focus and responsive styles."],
        },
        {
            "owner": "javascript-slm",
            "path": "app.js",
            "instructions": "Create bounded progressive enhancement behavior.",
            "acceptanceCriteria": ["Use no network or dynamic execution APIs."],
        },
    ],
}

HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Common Ground Studio</title>
    <link rel="stylesheet" href="styles.css">
    <script src="app.js" defer></script>
</head>
<body>
    <header><a href="#main">Common Ground</a></header>
    <main id="main"><h1>Make room for better ideas.</h1><button id="join">Join us</button></main>
</body>
</html>
"""

CSS = """body { margin: 0; font-family: sans-serif; }
:focus-visible { outline: 3px solid #245c4f; outline-offset: 3px; }
@media (max-width: 48rem) { body { padding: 1rem; } }
"""

REVISED_CSS = """body { margin: 0; font-family: system-ui, sans-serif; color: #172033; }
:focus-visible { outline: 3px solid #245c4f; outline-offset: 3px; }
@media (max-width: 48rem) { body { padding: 1.25rem; } }
"""

JAVASCRIPT = """"use strict";
const joinButton = document.querySelector("#join");
joinButton.addEventListener("click", () => joinButton.setAttribute("aria-pressed", "true"));
"""


class FakeModelClient:
    def __init__(
        self,
        model: str,
        responses: list[dict[str, Any]],
        *,
        ready: bool = True,
    ) -> None:
        self.model = model
        self.responses = list(responses)
        self.ready = ready
        self.calls: list[dict[str, Any]] = []
        self.last_usage = {"prompt_tokens": 11, "completion_tokens": 17}

    async def generate(self, *, prompt: str, json_schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"prompt": prompt, "json_schema": json_schema})
        if not self.responses:
            raise AssertionError(f"unexpected generation call to {self.model}")
        return self.responses.pop(0)

    async def readiness(self) -> SiteGenerationReadiness:
        return SiteGenerationReadiness(
            ready=self.ready,
            model=self.model,
            provider="injected",
            error=None if self.ready else "not ready",
        )


def _generator(
    *,
    head_reviews: list[dict[str, Any]] | None = None,
    html_responses: list[dict[str, Any]] | None = None,
    css_responses: list[dict[str, Any]] | None = None,
    javascript_responses: list[dict[str, Any]] | None = None,
    unavailable_role: str | None = None,
) -> tuple[OrchestratedSiteGenerator, dict[str, FakeModelClient]]:
    clients = {
        "head": FakeModelClient(
            "head-local:test",
            [PLAN, *(head_reviews or [{"verdict": "pass", "summary": "Integrated result is coherent.", "issues": []}])],
            ready=unavailable_role != "head",
        ),
        "html-slm": FakeModelClient(
            "helios-html-slm:test",
            html_responses or [{"path": "index.html", "content": HTML}],
            ready=unavailable_role != "html-slm",
        ),
        "css-slm": FakeModelClient(
            "helios-css-slm:test",
            css_responses or [{"path": "styles.css", "content": CSS}],
            ready=unavailable_role != "css-slm",
        ),
        "javascript-slm": FakeModelClient(
            "helios-javascript-slm:test",
            javascript_responses or [{"path": "app.js", "content": JAVASCRIPT}],
            ready=unavailable_role != "javascript-slm",
        ),
    }
    specialists = {
        role: SpecialistIdentity(
            role=role,  # type: ignore[arg-type]
            client=clients[role],
            base_model_id="gemma3:1b",
            specialization_id=f"helios-{role}-system-prompt",
            specialization_version="1.0",
            specialization_sha256=hashlib.sha256(role.encode()).hexdigest(),
        )
        for role in ("html-slm", "css-slm", "javascript-slm")
    }
    return OrchestratedSiteGenerator(clients["head"], specialists), clients


def _runtime(tmp_path) -> HeliosRuntime:
    settings = Settings(
        environment="test",
        helios_workspace_root=tmp_path / "workspace",
        helios_outbox_path=tmp_path / "workspace" / "outbox.jsonl",
        git_repo_cache_root=tmp_path / "workspace" / "repos",
    )
    return HeliosRuntime(settings, InMemoryControlPlane())


async def test_head_only_plans_and_reviews_while_three_slms_author_files(monkeypatch) -> None:
    generator, clients = _generator()
    updates: list[SiteGenerationProgress] = []

    async def capture(update: SiteGenerationProgress) -> None:
        updates.append(update)

    def reject_legacy_compiler(*_args, **_kwargs):
        raise AssertionError("legacy deterministic compiler must not author specialist files")

    monkeypatch.setattr("helios.site_generation._compile_site", reject_legacy_compiler)
    result = await generator.generate(
        SitePromptRequest(prompt="Build a community studio site."),
        on_progress=capture,
    )

    assert [file.content for file in result.files] == [HTML, CSS, JAVASCRIPT]
    assert [file.provenance.role for file in result.files if file.provenance] == [
        "html-slm",
        "css-slm",
        "javascript-slm",
    ]
    assert len(clients["head"].calls) == 2
    assert len(clients["html-slm"].calls) == 1
    assert len(clients["css-slm"].calls) == 1
    assert len(clients["javascript-slm"].calls) == 1
    for role in ("html-slm", "css-slm", "javascript-slm"):
        assert "messages" in clients[role].calls[0]["json_schema"]["required"]
        assert "Always return a messages array" in clients[role].calls[0]["prompt"]
    assert "index.html" in clients["head"].calls[-1]["prompt"]
    assert "Make room for better ideas." in clients["head"].calls[-1]["prompt"]
    assert "outline-offset" in clients["head"].calls[-1]["prompt"]
    assert "joinButton" in clients["head"].calls[-1]["prompt"]
    assert all(file.provenance.content_sha256 == hashlib.sha256(file.content.encode()).hexdigest()
               for file in result.files if file.provenance)
    assert result.head_review and result.head_review.approved
    assert result.head_review.rounds == 1
    assert [(item.stage, item.status) for item in updates] == [
        ("plan", "running"),
        ("plan", "completed"),
        ("html", "running"),
        ("html", "completed"),
        ("css", "running"),
        ("css", "completed"),
        ("javascript", "running"),
        ("javascript", "completed"),
        ("integrate", "running"),
        ("integrate", "completed"),
        ("review", "running"),
        ("review", "completed"),
        ("revise", "completed"),
        ("validate", "running"),
        ("validate", "completed"),
    ]


async def test_tagged_messages_are_recipient_scoped_and_preserve_transcript_order() -> None:
    tagged_plan = {
        **PLAN,
        "messages": [
            {"to": "@html", "kind": "handoff", "body": "HEAD_TO_HTML"},
            {"to": "@javascript", "kind": "handoff", "body": "HEAD_TO_JAVASCRIPT"},
        ],
    }
    generator, clients = _generator(
        html_responses=[{
            "path": "index.html",
            "content": HTML,
            "messages": [
                {"to": "@css", "kind": "handoff", "body": "HTML_TO_CSS"},
                {"to": "@head", "kind": "risk", "body": "HTML_TO_HEAD"},
            ],
        }],
        css_responses=[{
            "path": "styles.css",
            "content": CSS,
            "messages": [
                {"to": "@javascript", "kind": "handoff", "body": "CSS_TO_JAVASCRIPT"},
                {"to": "@head", "kind": "question", "body": "CSS_TO_HEAD"},
            ],
        }],
        javascript_responses=[{
            "path": "app.js",
            "content": JAVASCRIPT,
            "messages": [
                {"to": "@head", "kind": "answer", "body": "JAVASCRIPT_TO_HEAD"},
            ],
        }],
    )
    clients["head"].responses[0] = tagged_plan

    result = await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    html_prompt = clients["html-slm"].calls[0]["prompt"]
    css_prompt = clients["css-slm"].calls[0]["prompt"]
    javascript_prompt = clients["javascript-slm"].calls[0]["prompt"]
    review_prompt = clients["head"].calls[-1]["prompt"]
    assert "HEAD_TO_HTML" in html_prompt
    assert "HEAD_TO_JAVASCRIPT" not in html_prompt
    assert "HTML_TO_CSS" in css_prompt
    assert "HEAD_TO_HTML" not in css_prompt
    assert "HEAD_TO_JAVASCRIPT" in javascript_prompt
    assert "CSS_TO_JAVASCRIPT" in javascript_prompt
    assert javascript_prompt.index("HEAD_TO_JAVASCRIPT") < javascript_prompt.index("CSS_TO_JAVASCRIPT")
    assert "HTML_TO_CSS" not in javascript_prompt
    for direct_head_message in ("HTML_TO_HEAD", "CSS_TO_HEAD", "JAVASCRIPT_TO_HEAD"):
        assert direct_head_message in review_prompt
    for specialist_message in ("HEAD_TO_HTML", "HEAD_TO_JAVASCRIPT", "HTML_TO_CSS", "CSS_TO_JAVASCRIPT"):
        assert specialist_message not in review_prompt

    assert [message.sequence for message in result.agent_messages] == list(range(1, 8))
    assert [message.body for message in result.agent_messages] == [
        "HEAD_TO_HTML",
        "HEAD_TO_JAVASCRIPT",
        "HTML_TO_CSS",
        "HTML_TO_HEAD",
        "CSS_TO_JAVASCRIPT",
        "CSS_TO_HEAD",
        "JAVASCRIPT_TO_HEAD",
    ]
    assert [message.sender for message in result.agent_messages] == [
        "head",
        "head",
        "html-slm",
        "html-slm",
        "css-slm",
        "css-slm",
        "javascript-slm",
    ]
    assert [message.recipient for message in result.agent_messages] == [
        "html-slm",
        "javascript-slm",
        "css-slm",
        "head",
        "javascript-slm",
        "head",
        "head",
    ]
    assert [message.tag for message in result.agent_messages] == [
        "@html",
        "@javascript",
        "@css",
        "@head",
        "@javascript",
        "@head",
        "@head",
    ]
    assert [message.phase for message in result.agent_messages] == [
        "plan",
        "plan",
        "html",
        "html",
        "css",
        "css",
        "javascript",
    ]
    assert [message.delivery for message in result.agent_messages] == [
        "direct",
        "direct",
        "direct",
        "head-review",
        "direct",
        "head-review",
        "head-review",
    ]
    assert [message.model for message in result.agent_messages] == [
        "head-local:test",
        "head-local:test",
        "helios-html-slm:test",
        "helios-html-slm:test",
        "helios-css-slm:test",
        "helios-css-slm:test",
        "helios-javascript-slm:test",
    ]
    assert all(message.model_digest is None for message in result.agent_messages)


async def test_message_body_mentions_do_not_change_structured_routing() -> None:
    body = "BODY_MENTION_SENTINEL asks @css and @javascript, but this is for the head."
    generator, clients = _generator(html_responses=[{
        "path": "index.html",
        "content": HTML,
        "messages": [{"to": "@head", "kind": "question", "body": body}],
    }])

    result = await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert body not in clients["css-slm"].calls[0]["prompt"]
    assert body not in clients["javascript-slm"].calls[0]["prompt"]
    assert body in clients["head"].calls[-1]["prompt"]
    assert [(message.tag, message.body) for message in result.agent_messages] == [
        ("@head", body),
    ]


async def test_head_routes_one_revision_only_to_the_responsible_slm() -> None:
    generator, clients = _generator(
        head_reviews=[
            {
                "verdict": "revise",
                "summary": "CSS needs stronger readable defaults.",
                "issues": [
                    {
                        "issueId": "css-readable",
                        "owner": "css-slm",
                        "path": "styles.css",
                        "tag": "@css",
                        "message": "Add an explicit readable foreground color.",
                    }
                ],
            },
            {"verdict": "pass", "summary": "Revised project is coherent.", "issues": []},
        ],
        css_responses=[
            {"path": "styles.css", "content": CSS},
            {"path": "styles.css", "content": REVISED_CSS},
        ],
    )

    result = await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert result.files[1].content == REVISED_CSS
    assert result.files[0].content == HTML
    assert result.files[2].content == JAVASCRIPT
    assert len(clients["head"].calls) == 3
    assert len(clients["css-slm"].calls) == 2
    assert len(clients["html-slm"].calls) == 1
    assert len(clients["javascript-slm"].calls) == 1
    assert result.files[1].provenance and result.files[1].provenance.revision == 1
    assert result.files[1].provenance.attempt == 2
    assert result.head_review and result.head_review.rounds == 2
    assert "@css" in clients["css-slm"].calls[-1]["prompt"]
    assert "Add an explicit readable foreground color." in clients["css-slm"].calls[-1]["prompt"]
    assert [
        (message.sender, message.recipient, message.tag, message.phase, message.body)
        for message in result.agent_messages
    ] == [
        (
            "head",
            "css-slm",
            "@css",
            "review",
            "Add an explicit readable foreground color.",
        ),
    ]


@pytest.mark.parametrize(
    ("role", "invalid_tag"),
    [
        ("html-slm", "@scss"),
        ("html-slm", "@html"),
        ("html-slm", "@ css"),
        ("css-slm", "@html"),
        ("javascript-slm", "@css"),
    ],
)
async def test_invalid_self_or_backward_tag_is_repaired_without_delivery(
    role: str,
    invalid_tag: str,
) -> None:
    role_output = {
        "html-slm": ("index.html", HTML, "html_responses"),
        "css-slm": ("styles.css", CSS, "css_responses"),
        "javascript-slm": ("app.js", JAVASCRIPT, "javascript_responses"),
    }
    path, content, response_argument = role_output[role]
    invalid_body = f"INVALID_MESSAGE_{role}_{invalid_tag}"
    responses = [
        {
            "path": path,
            "content": content,
            "messages": [{"to": invalid_tag, "kind": "question", "body": invalid_body}],
        },
        {"path": path, "content": content, "messages": []},
    ]
    generator, clients = _generator(**{response_argument: responses})

    result = await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert len(clients[role].calls) == 2
    assert all(
        len(client.calls) == (2 if name == role else 1)
        for name, client in clients.items()
        if name != "head"
    )
    assert len(clients["head"].calls) == 2
    assert all(message.body != invalid_body for message in result.agent_messages)
    owned_file = next(file for file in result.files if file.provenance and file.provenance.role == role)
    assert owned_file.provenance and owned_file.provenance.attempt == 2


async def test_backward_tag_fails_closed_after_one_repair_without_extra_calls() -> None:
    invalid_css = {
        "path": "styles.css",
        "content": CSS,
        "messages": [{"to": "@html", "kind": "question", "body": "BACKWARD_TO_HTML"}],
    }
    generator, clients = _generator(css_responses=[invalid_css, invalid_css])

    with pytest.raises(
        SiteGenerationError,
        match="css-slm returned invalid styles.css after one repair attempt",
    ):
        await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert len(clients["head"].calls) == 1
    assert len(clients["html-slm"].calls) == 1
    assert len(clients["css-slm"].calls) == 2
    assert len(clients["javascript-slm"].calls) == 0


async def test_code_in_handoff_is_repaired_before_delivery() -> None:
    invalid_body = "Style #join with .button { color: red; }"
    valid_body = "Preserve the join button hook and provide a visible focus treatment."
    generator, clients = _generator(html_responses=[
        {
            "path": "index.html",
            "content": HTML,
            "messages": [{"to": "@css", "kind": "handoff", "body": invalid_body}],
        },
        {
            "path": "index.html",
            "content": HTML,
            "messages": [{"to": "@css", "kind": "handoff", "body": valid_body}],
        },
    ])

    result = await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert len(clients["html-slm"].calls) == 2
    assert [message.body for message in result.agent_messages] == [valid_body]
    assert invalid_body not in clients["css-slm"].calls[0]["prompt"]
    assert valid_body in clients["css-slm"].calls[0]["prompt"]
    assert result.files[0].provenance and result.files[0].provenance.attempt == 2


async def test_head_review_rejects_a_tag_that_does_not_match_the_file_owner() -> None:
    mismatched_review = {
        "verdict": "revise",
        "summary": "The tag attempts to route the CSS issue to HTML.",
        "issues": [
            {
                "issueId": "css-tag-mismatch",
                "owner": "css-slm",
                "path": "styles.css",
                "tag": "@html",
                "message": "Add an explicit readable foreground color.",
            },
        ],
    }
    generator, clients = _generator(head_reviews=[mismatched_review, mismatched_review])

    with pytest.raises(
        SiteGenerationError,
        match="Head returned an invalid review after one repair attempt",
    ):
        await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert len(clients["head"].calls) == 3
    assert len(clients["html-slm"].calls) == 1
    assert len(clients["css-slm"].calls) == 1
    assert len(clients["javascript-slm"].calls) == 1


async def test_html_self_repair_restates_the_mandatory_asset_contract() -> None:
    invalid_html = HTML.replace(
        '    <link rel="stylesheet" href="styles.css">\n',
        "",
    ).replace(
        '    <script src="app.js" defer></script>\n',
        "",
    )
    generator, clients = _generator(html_responses=[
        {"path": "index.html", "content": invalid_html},
        {"path": "index.html", "content": HTML},
    ])

    result = await generator.generate(SitePromptRequest(prompt="Build a community studio site."))

    assert result.files[0].content == HTML
    assert len(clients["html-slm"].calls) == 2
    initial_prompt = clients["html-slm"].calls[0]["prompt"]
    repair_prompt = clients["html-slm"].calls[1]["prompt"]
    for required_contract in (
        "<!doctype html>",
        '<html lang="en">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<link rel="stylesheet" href="styles.css">',
        '<script src="app.js" defer></script>',
        "exactly one main landmark",
        "exactly one h1",
        "style attributes",
    ):
        assert required_contract in initial_prompt
        assert required_contract in repair_prompt
    assert "Discard it and rebuild the complete file from scratch" in repair_prompt
    assert "SPECIALIST_CONTEXT_JSON=" in repair_prompt
    assert "INVALID_OUTPUT=" not in repair_prompt
    assert result.files[0].provenance and result.files[0].provenance.attempt == 2


@pytest.mark.parametrize("unavailable_role", ["head", "html-slm", "css-slm", "javascript-slm"])
async def test_generation_fails_closed_before_any_model_call(unavailable_role: str) -> None:
    generator, clients = _generator(unavailable_role=unavailable_role)

    readiness = await generator.readiness()
    assert readiness.ready is False
    assert unavailable_role in (readiness.error or "")
    with pytest.raises(SiteGenerationError, match=unavailable_role):
        await generator.generate(SitePromptRequest(prompt="Build a community studio site."))
    assert all(not client.calls for client in clients.values())


def test_rest_and_websocket_expose_truthful_pipeline_and_provenance(tmp_path) -> None:
    tagged_html_response = {
        "path": "index.html",
        "content": HTML,
        "messages": [
            {"to": "@css", "kind": "handoff", "body": "STREAM_HTML_TO_CSS"},
        ],
    }
    tagged_javascript_response = {
        "path": "app.js",
        "content": JAVASCRIPT,
        "messages": [
            {"to": "@head", "kind": "answer", "body": "STREAM_JAVASCRIPT_TO_HEAD"},
        ],
    }
    generator, _ = _generator(
        html_responses=[tagged_html_response],
        javascript_responses=[tagged_javascript_response],
    )
    app = create_app(_runtime(tmp_path), site_generator=generator)
    client = TestClient(app)

    response = client.post("/generate/site", json={"prompt": "Build a community studio site."})
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "head-local:test"
    assert [item["provenance"]["role"] for item in payload["files"]] == [
        "html-slm",
        "css-slm",
        "javascript-slm",
    ]
    assert [item["body"] for item in payload["agentMessages"]] == [
        "STREAM_HTML_TO_CSS",
        "STREAM_JAVASCRIPT_TO_HEAD",
    ]
    assert [item["sequence"] for item in payload["agentMessages"]] == [1, 2]
    assert all({
        "sequence",
        "sender",
        "recipient",
        "tag",
        "kind",
        "phase",
        "delivery",
        "body",
        "model",
        "modelDigest",
    } <= set(item) for item in payload["agentMessages"])
    readiness = client.get("/health/site").json()
    assert readiness["ready"] is True
    assert [item["role"] for item in readiness["roles"]] == [
        "head",
        "html-slm",
        "css-slm",
        "javascript-slm",
    ]

    websocket_generator, _ = _generator(
        html_responses=[tagged_html_response],
        javascript_responses=[tagged_javascript_response],
    )
    websocket_app = create_app(_runtime(tmp_path / "ws"), site_generator=websocket_generator)
    with TestClient(websocket_app).websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "prompt", "data": "Build a community studio site."})
        messages = []
        while not messages or messages[-1]["type"] != "complete":
            messages.append(websocket.receive_json())

    plan = messages[0]["data"]
    assert [node["id"] for node in plan["nodes"]] == [
        "plan",
        "html",
        "css",
        "javascript",
        "integrate",
        "review",
        "revise",
        "validate",
        "deliver",
    ]
    artifacts = [message for message in messages if message["type"] == "artifact"]
    assert [item["provenance"]["role"] for item in artifacts] == [
        "html-slm",
        "css-slm",
        "javascript-slm",
    ]
    assert messages[-1]["headReview"]["approved"] is True
    assert [item["body"] for item in messages[-1]["agentMessages"]] == [
        "STREAM_HTML_TO_CSS",
        "STREAM_JAVASCRIPT_TO_HEAD",
    ]
    streamed_messages = [
        message["data"]
        for message in messages
        if message["type"] == "agent_message"
    ]
    assert [item["body"] for item in streamed_messages] == [
        "STREAM_HTML_TO_CSS",
        "STREAM_JAVASCRIPT_TO_HEAD",
    ]
    html_to_css_event = next(
        index
        for index, message in enumerate(messages)
        if message["type"] == "agent_message"
        and message["data"]["body"] == "STREAM_HTML_TO_CSS"
    )
    css_running_event = next(
        index
        for index, message in enumerate(messages)
        if message["type"] == "plan_node_status"
        and message["data"]["nodeId"] == "css"
        and message["data"]["status"] == "running"
    )
    assert html_to_css_event < css_running_event
    assert {item["role"] for item in messages[-1]["modelInvocations"]} == {
        "head",
        "html-slm",
        "css-slm",
        "javascript-slm",
    }
