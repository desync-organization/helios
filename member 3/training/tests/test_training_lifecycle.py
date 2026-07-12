from __future__ import annotations

from pathlib import Path

import pytest
from hermes_training.adapter_manifest import PromotionEvidence, evaluate_promotion
from hermes_training.environment import require_training_environment
from hermes_training.training_config import TrainingConfig
from pydantic import ValidationError


def valid_config() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "run_name": "triage-qwen3-r16",
        "base_model_id": "Qwen/Qwen3-4B",
        "base_model_revision": "0123456789abcdef",
        "base_model_sha256": "a" * 64,
        "tokenizer_sha256": "b" * 64,
        "dataset_manifest": Path("datasets/manifests/triage-v1.json"),
        "output_root": Path("training/runs"),
        "method": "qlora",
        "compute_dtype": "bf16",
        "quantization": {"bits": 4, "quant_type": "nf4", "double_quant": True},
        "lora": {
            "rank": 16,
            "alpha": 32,
            "dropout": 0.05,
            "target_modules": ["q_proj", "v_proj"],
        },
        "training": {
            "epochs": 2,
            "learning_rate": 0.0002,
            "max_length": 2048,
            "batch_size": 1,
            "gradient_accumulation_steps": 16,
            "warmup_ratio": 0.03,
            "weight_decay": 0.01,
            "logging_steps": 5,
            "seed": 3407,
            "packing": False,
            "assistant_only_loss": True,
        },
    }


def test_training_config_requires_verified_pins() -> None:
    values = valid_config()
    values["base_model_revision"] = "<pin-me>"
    with pytest.raises(ValidationError, match="verified values"):
        TrainingConfig.model_validate(values)


def test_training_environment_fails_honestly_without_optional_stack() -> None:
    with pytest.raises(RuntimeError, match=r"training dependencies|supported GPU"):
        require_training_environment(compute_dtype="bf16")


def promotion_evidence(**updates: object) -> PromotionEvidence:
    values: dict[str, object] = {
        "primaryMetricBase": 0.85,
        "primaryMetricCandidate": 0.88,
        "minimumImprovement": 0.02,
        "maintainerPassRate": 0.88,
        "secretLeakCount": 0,
        "unauthorizedActionCount": 0,
        "criticalSubgroupRegression": False,
        "fastLaneLatencySeconds": 44.0,
        "memoryFitsDemoMachine": True,
        "stableRunReportSha256s": ["a" * 64, "b" * 64, "c" * 64],
        "member1LoaderSmokePassed": True,
        "member2AtomicActivationPassed": True,
        "rollbackDemonstrated": True,
        "criticIsIndependent": True,
    }
    values.update(updates)
    return PromotionEvidence.model_validate(values)


def test_promotion_passes_only_with_all_evidence() -> None:
    assert evaluate_promotion(promotion_evidence()).passed is True


def test_secret_leak_blocks_promotion_regardless_of_score() -> None:
    decision = evaluate_promotion(
        promotion_evidence(primaryMetricCandidate=1.0, secretLeakCount=1)
    )
    assert decision.passed is False
    assert "secret leak automatic failure" in decision.blockers
