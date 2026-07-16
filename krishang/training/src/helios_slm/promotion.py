from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SpecialistSpec, require_pinned_models
from .dataset import sha256_file
from .evaluation import load_passing_eval_report


def create_promotion_manifest(
    spec: SpecialistSpec,
    *,
    adapter_path: Path,
    base_model_path: Path,
    tokenizer_path: Path,
    dataset_manifest_path: Path,
    eval_report_path: Path,
    training_run_id: str,
    destination: Path,
) -> dict[str, Any]:
    require_pinned_models(spec)
    required = (
        adapter_path,
        base_model_path,
        tokenizer_path,
        dataset_manifest_path,
        eval_report_path,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("promotion inputs are missing: " + ", ".join(missing))
    if adapter_path.suffix.lower() != ".gguf":
        raise ValueError(
            "runtime promotion requires a llama.cpp-compatible GGUF LoRA adapter"
        )
    load_passing_eval_report(eval_report_path)
    payload = {
        "adapterId": spec.adapter.adapter_id,
        "adapterVersion": spec.adapter.adapter_version,
        "adapterSha256": sha256_file(adapter_path),
        "adapterPath": str(adapter_path.resolve()),
        "format": "gguf-lora",
        "baseModelId": spec.model.student_id,
        "baseModelRevision": spec.model.student_revision,
        "baseModelSha256": sha256_file(base_model_path),
        "tokenizerSha256": sha256_file(tokenizer_path),
        "targetRoles": [spec.role],
        "trainingRunId": training_run_id,
        "datasetManifestSha256": sha256_file(dataset_manifest_path),
        "lora": {
            "rank": spec.adapter.rank,
            "alpha": spec.adapter.alpha,
            "dropout": spec.adapter.dropout,
            "targetModules": spec.adapter.target_modules,
        },
        "quantization": spec.adapter.quantization,
        "evalReportSha256": sha256_file(eval_report_path),
        "promotedAt": datetime.now(timezone.utc).isoformat(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(destination)
    return payload
