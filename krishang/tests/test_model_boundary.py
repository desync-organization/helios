from __future__ import annotations

import hashlib
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from helios.evals.member3 import load_member3_evaluator, run_member3_evaluation
from helios.models.client import LlamaClient, ModelEndpointStatus
from helios.models.manager import ModelManager
from helios.models.registry import ModelDefinition
from helios.models.slm import (
    SlmServerSpec,
    sanitized_server_environment,
    supervise_servers,
)


TRAINING_SOURCE = Path(__file__).parents[1] / "training" / "src"
if str(TRAINING_SOURCE) not in sys.path:
    sys.path.insert(0, str(TRAINING_SOURCE))

from helios_slm.config import load_spec  # noqa: E402
from helios_slm.dataset import DatasetRecord, DatasetValidationError, validate_records  # noqa: E402
from helios_slm.distill import distill  # noqa: E402
from helios_slm.evaluation import load_passing_eval_report  # noqa: E402


async def test_llama_probe_and_completion_require_exact_model_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "expected-model"}]})
        return httpx.Response(
            200,
            json={"model": "expected-model", "choices": []},
        )

    client = LlamaClient(
        "http://127.0.0.1:8080",
        timeout=1,
        expected_model_id="expected-model",
        transport=httpx.MockTransport(handler),
    )
    assert (await client.probe()).ready is True
    verified_client = LlamaClient(
        "http://127.0.0.1:8080", timeout=1, transport=httpx.MockTransport(handler)
    )
    assert verified_client.expected_model_id == "expected-model"
    response = await verified_client.completion(
        messages=[], json_schema={}, max_tokens=1
    )
    assert response["model"] == "expected-model"

    mismatch = await client.probe("different-model")
    assert mismatch.ready is False
    assert mismatch.advertised_model_ids == ["expected-model"]
    assert mismatch.error == "model server advertised an unexpected identity"


async def test_model_manager_counts_shared_physical_server_once() -> None:
    registry = {
        role: ModelDefinition(
            model_id="shared",
            role=role,
            endpoint="http://127.0.0.1:8080",
            quantization="q4",
            estimated_vram_mb=8,
            hot=True,
            tier="local",
        )
        for role in ("planner", "critic")
    }
    manager = ModelManager(registry, max_vram_mb=8)
    await manager.acquire("planner")
    await manager.acquire("critic")
    assert manager._used_vram() == 8
    assert manager.events[-1].type == "model_shared_reuse"


async def test_model_manager_rejects_unexpected_server_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(200, json={"data": [{"id": "wrong-model"}]})

    definition = ModelDefinition(
        model_id="expected-model",
        role="planner",
        endpoint="http://127.0.0.1:8080",
        quantization="q4",
        estimated_vram_mb=8,
        hot=True,
        tier="local",
        expected_server_id="expected-model",
        verify_identity=True,
    )
    manager = ModelManager(
        {"planner": definition},
        max_vram_mb=8,
        probe_transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ConnectionError, match="unexpected identity"):
        await manager.acquire("planner")
    assert manager.loaded == {}


async def test_real_member3_evaluator_interface_runs_one_case() -> None:
    evaluator = load_member3_evaluator()
    assert evaluator.__name__ == "hermes_evals"
    case_path = (
        Path(__file__).parents[2] / "member 3" / "evals" / "gauntlet" / "cases-v1.jsonl"
    )
    case = json.loads(case_path.read_text(encoding="utf-8").splitlines()[0])
    result = {
        "caseId": case["caseId"],
        "configuration": "focused-boundary-test",
        "seed": 42,
        "output": {"classification": "bug", "priority": "p2", "labels": ["bug"]},
        "telemetry": {
            "tokensIn": 1,
            "tokensOut": 1,
            "latencyMs": 1,
            "peakRamMb": 1,
            "peakVramMb": 0,
            "costUsd": 0,
            "costCloudEquivalentUsd": 0,
            "executionLocation": "local",
            "coldStart": False,
        },
    }
    report = await run_member3_evaluation({"cases": [case], "results": [result]})
    assert report["gatePassed"] is True
    assert report["caseCount"] == 1


def _eval_report(*, passed: bool = True) -> dict:
    telemetry = {
        "tokensIn": 1,
        "tokensOut": 1,
        "latencyMs": 1,
        "peakRamMb": 1,
        "peakVramMb": 0,
        "costUsd": 0,
        "costCloudEquivalentUsd": 0,
        "executionLocation": "local",
        "coldStart": False,
    }
    return {
        "schemaVersion": "1.0",
        "reportId": "eval-focused",
        "configuration": "gemma-html-lora@1.0",
        "seed": 42,
        "caseSetSha256": "a" * 64,
        "createdAt": "2026-07-12T00:00:00Z",
        "caseCount": 1,
        "passedCount": int(passed),
        "passRate": float(passed),
        "categoryPassRates": {"web-slm": float(passed)},
        "automaticFailureCount": 0,
        "gatePassed": passed,
        "gateBlockers": [] if passed else ["failed"],
        "totalTokensIn": 1,
        "totalTokensOut": 1,
        "totalCostUsd": 0,
        "totalCloudEquivalentCostUsd": 0,
        "latencyP50Ms": 1,
        "latencyP95Ms": 1,
        "securityMetrics": None,
        "cases": [
            {
                "caseId": "web-slm-1",
                "suite": "build",
                "category": "web-slm",
                "passed": passed,
                "score": float(passed),
                "automaticFailure": False,
                "checks": [
                    {
                        "kind": "equals",
                        "path": "valid",
                        "passed": passed,
                        "automaticFailure": False,
                        "reason": "fixture",
                    }
                ],
                "telemetry": telemetry,
            }
        ],
    }


def test_promotion_eval_requires_valid_schema_and_passing_gate(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_eval_report()), encoding="utf-8")
    assert load_passing_eval_report(report_path).gate_passed is True

    report_path.write_text(json.dumps(_eval_report(passed=False)), encoding="utf-8")
    with pytest.raises(ValueError, match="gate did not pass"):
        load_passing_eval_report(report_path)


def test_dataset_teacher_trace_must_match_pinned_identity() -> None:
    response = "<main>Hello</main>"
    record = DatasetRecord.model_validate(
        {
            "schemaVersion": "1.0",
            "exampleId": "html-1",
            "role": "html-slm",
            "split": "train",
            "instruction": "Make a main region",
            "response": response,
            "source": "fixture",
            "license": "CC0-1.0",
            "consent": "synthetic",
            "teacher": {
                "modelId": "wrong/teacher",
                "modelRevision": "b" * 40,
                "responseSha256": hashlib.sha256(response.encode()).hexdigest(),
            },
        }
    )
    with pytest.raises(DatasetValidationError, match="modelId"):
        validate_records(
            [record],
            require_teacher=True,
            expected_teacher_id="google/gemma-3-4b-it",
            expected_teacher_revision="b" * 40,
        )


def test_distillation_uses_gemma3_multimodal_interface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = load_spec(Path(__file__).parents[1] / "training" / "configs" / "html.yaml")
    spec.model.student_revision = "a" * 40
    spec.model.teacher_revision = "b" * 40
    calls: dict[str, object] = {}

    class Inputs(dict):
        def to(self, device: str) -> "Inputs":
            calls["device"] = device
            return self

    class Processor:
        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs):
            calls["processor"] = (model_id, kwargs)
            return cls()

        def apply_chat_template(self, messages, **kwargs):
            calls["messages"] = messages
            calls["template_kwargs"] = kwargs
            return Inputs(input_ids=SimpleNamespace(shape=(1, 3)))

        def decode(self, tokens, **kwargs):
            return "<main>Hello</main>"

    class Model:
        device = "cpu"
        config = SimpleNamespace(
            model_type="gemma3",
            _name_or_path="google/gemma-3-4b-it",
            _commit_hash="b" * 40,
        )

        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs):
            calls["model"] = (model_id, kwargs)
            return cls()

        def eval(self) -> "Model":
            return self

        def generate(self, **kwargs):
            calls["generate"] = kwargs
            return [[0, 1, 2, 3]]

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoProcessor=Processor,
            Gemma3ForConditionalGeneration=Model,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(bfloat16="bf16", inference_mode=nullcontext),
    )
    source = tmp_path / "source.jsonl"
    source.write_text(
        json.dumps(
            {
                "exampleId": "html-1",
                "split": "train",
                "instruction": "Make a main region",
                "context": {},
                "source": "fixture",
                "license": "CC0-1.0",
                "consent": "synthetic",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "distilled.jsonl"
    distill(spec, source, destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["teacher"]["modelId"] == "google/gemma-3-4b-it"
    assert calls["template_kwargs"] == {
        "add_generation_prompt": True,
        "tokenize": True,
        "return_dict": True,
        "return_tensors": "pt",
    }


async def test_slm_supervisor_tears_down_all_servers_on_one_exit() -> None:
    assert sanitized_server_environment(
        {"PATH": "bin", "GITHUB_APP_PRIVATE_KEY": "secret"}
    ) == {"PATH": "bin"}

    class Process:
        def __init__(self, fail: bool) -> None:
            self.fail = fail
            self.polls = 0
            self.returncode = None
            self.terminated = False

        def poll(self):
            self.polls += 1
            if self.fail and self.polls >= 2:
                self.returncode = 9
            if self.terminated and self.returncode is None:
                self.returncode = 0
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float):
            self.returncode = 0 if self.returncode is None else self.returncode
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    processes = [Process(False), Process(True)]

    def popen(*args, **kwargs):
        return processes.pop(0)

    launched: list[Process] = []
    source_processes = [Process(False), Process(True)]

    def tracked_popen(*args, **kwargs):
        process = source_processes[len(launched)]
        launched.append(process)
        return process

    async def ready(spec: SlmServerSpec) -> ModelEndpointStatus:
        return ModelEndpointStatus(
            endpoint=spec.endpoint,
            ready=True,
            expected_model_id=spec.server_identity,
            advertised_model_ids=[spec.server_identity],
        )

    specs = {
        role: SlmServerSpec(
            role=role,
            endpoint=f"http://127.0.0.1:{8080 + index}",
            server_identity=role,
            command=("llama-server", "--alias", role),
        )
        for index, role in enumerate(("html-slm", "css-slm"))
    }
    with pytest.raises(RuntimeError, match="exited unexpectedly"):
        await supervise_servers(
            specs,
            poll_interval_s=0,
            popen_factory=tracked_popen,
            readiness_probe=ready,
        )
    assert all(process.returncode is not None for process in launched)
