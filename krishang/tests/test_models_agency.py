import hashlib
import json

import pytest

from helios.agency.adjust import adjust_persona
from helios.agency.registry import AgentRegistry
from helios.agency.spawn import spawn_rust_fixture
from helios.models.adapters import AdapterLoader
from helios.models.manager import ModelManager
from helios.models.registry import ModelDefinition


async def test_model_cold_load_warm_reuse_and_eviction():
    registry = {
        "hot": ModelDefinition(model_id="hot", role="hot", endpoint="one", quantization="q4",
                               estimated_vram_mb=4, hot=True, tier="local-4b"),
        "cold-a": ModelDefinition(model_id="a", role="a", endpoint="two", quantization="q4",
                                  estimated_vram_mb=5, tier="local-coder"),
        "cold-b": ModelDefinition(model_id="b", role="b", endpoint="three", quantization="q4",
                                  estimated_vram_mb=5, tier="local-coder"),
    }
    manager = ModelManager(registry, 10)
    await manager.acquire("hot")
    await manager.acquire("cold-a")
    await manager.acquire("cold-a")
    await manager.acquire("cold-b")
    assert [event.type for event in manager.events] == ["model_loaded", "model_loaded", "model_warm_reuse", "model_evicted", "model_loaded"]
    assert "hot" in manager.loaded and "cold-a" not in manager.loaded


def test_adapter_hash_verification_and_rollback(tmp_path):
    base = tmp_path / "base.gguf"
    adapter = tmp_path / "adapter.gguf"
    base.write_bytes(b"base")
    adapter.write_bytes(b"adapter")
    manifest = {
        "adapterId": "triage-lora", "adapterVersion": "1", "adapterSha256": hashlib.sha256(b"adapter").hexdigest(),
        "adapterPath": str(adapter), "format": "gguf-lora", "baseModelId": "qwen3-4b", "baseModelRevision": "r1",
        "baseModelSha256": hashlib.sha256(b"base").hexdigest(), "tokenizerSha256": "t" * 64,
        "targetRoles": ["triage"], "trainingRunId": "train-1", "datasetManifestSha256": "d" * 64,
        "lora": {"rank": 8, "alpha": 16, "dropout": 0.05, "targetModules": ["q_proj"]},
        "quantization": "q4", "evalReportSha256": "e" * 64, "promotedAt": "2026-07-12T00:00:00Z",
    }
    path = tmp_path / "active.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loader = AdapterLoader(path)
    loaded = loader.load(base)
    assert loaded.adapter_id == "triage-lora" and loader.for_role("triage")
    assert loader.for_critic("triage-lora") is None
    loader.rollback()
    assert loader.active is None
    adapter.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        loader.load(base)


def test_rust_expert_spawns_and_role_adjustment_is_bounded():
    registry = AgentRegistry()
    agent, event = spawn_rust_fixture(registry, "run-1")
    assert agent.origin == "spawned" and event.type == "agent_spawned"
    adjusted = adjust_persona(agent, "Always cite the failing cargo test", 2)
    assert adjusted.version != agent.version
    with pytest.raises(PermissionError):
        adjust_persona(agent, "Change tool guardrail", 2)
