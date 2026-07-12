"""Capture reproducibility metadata without copying environment variables or credentials."""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from datetime import UTC, datetime
from typing import Any

TRACKED_PACKAGES = (
    "accelerate",
    "bitsandbytes",
    "datasets",
    "peft",
    "safetensors",
    "torch",
    "transformers",
    "trl",
)


def capture_environment() -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    for package in TRACKED_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    gpu: dict[str, Any] = {"available": False}
    try:
        import torch  # type: ignore[import-not-found]

        gpu = {
            "available": torch.cuda.is_available(),
            "count": torch.cuda.device_count(),
            "bf16Supported": torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
            "devices": [
                torch.cuda.get_device_name(index)
                for index in range(torch.cuda.device_count())
            ],
        }
    except ImportError:
        pass
    return {
        "capturedAt": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": versions,
        "gpu": gpu,
    }


def require_training_environment(*, compute_dtype: str) -> dict[str, Any]:
    environment = capture_environment()
    missing = [
        package
        for package, version in environment["packages"].items()
        if version is None
    ]
    if missing:
        raise RuntimeError(
            "training dependencies are unavailable; install .[training]: " + ", ".join(missing)
        )
    gpu = environment["gpu"]
    if not gpu["available"]:
        raise RuntimeError("QLoRA/LoRA training requires a supported GPU")
    if compute_dtype == "bf16" and not gpu["bf16Supported"]:
        raise RuntimeError("bf16 was requested but the detected GPU does not support it")
    return environment
