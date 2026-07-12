import json
from pathlib import Path

import httpx

from helios.api import create_app
from helios.config import Settings
from helios.contracts import CanonicalEvent, NormalizedTask
from helios.control_plane import InMemoryControlPlane
from helios.runtime import HeliosRuntime


FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_shared_json_fixtures_round_trip():
    task_payload = json.loads((FIXTURES / "task.json").read_text(encoding="utf-8"))
    event_payload = json.loads((FIXTURES / "canonical_event.json").read_text(encoding="utf-8"))
    task = NormalizedTask.model_validate(task_payload)
    event = CanonicalEvent.model_validate(event_payload)
    assert task.model_dump(mode="json", by_alias=True) == task_payload
    assert event.model_dump(mode="json", by_alias=True) == event_payload


async def test_local_mutations_require_token_and_exact_origin(tmp_path):
    settings = Settings(helios_workspace_root=tmp_path, git_repo_cache_root=tmp_path / "repos",
                        helios_outbox_path=tmp_path / "outbox.jsonl", helios_local_api_token="test-token",
                        helios_allowed_origin="http://127.0.0.1:3000")
    runtime = HeliosRuntime(settings, InMemoryControlPlane())
    transport = httpx.ASGITransport(app=create_app(runtime))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.post("/control/pause")
        assert unauthorized.status_code == 401
        authorized = await client.post("/control/pause", headers={"Authorization": "Bearer test-token"})
        assert authorized.status_code == 200 and authorized.json()["paused"] is True
        preflight = await client.options("/control/pause", headers={
            "Origin": "http://127.0.0.1:3000", "Access-Control-Request-Method": "POST",
        })
        assert preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
        denied_origin = await client.options("/control/pause", headers={
            "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
        })
        assert "access-control-allow-origin" not in denied_origin.headers

