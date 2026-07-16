from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from helios.config import Settings
from helios.contracts.adapter import AdapterManifest

from .client import LlamaClient, ModelEndpointStatus


ROLE_SETTINGS = {
    "html-slm": ("html-active.json", "llama_html_slm_url"),
    "css-slm": ("css-active.json", "llama_css_slm_url"),
    "javascript-slm": ("javascript-active.json", "llama_javascript_slm_url"),
}


@dataclass(frozen=True)
class SlmServerSpec:
    role: str
    endpoint: str
    server_identity: str
    command: tuple[str, ...]


def promoted_manifest_root() -> Path:
    return Path(__file__).resolve().parents[3] / "adapters" / "promoted"


def server_identity(role: str, manifest: AdapterManifest) -> str:
    """Build the exact identity advertised by the verified llama.cpp process."""

    raw = (
        f"helios-{role}-{manifest.adapter_id}-{manifest.adapter_version}-"
        f"{manifest.adapter_sha256[:12]}"
    )
    return re.sub(r"[^A-Za-z0-9_.-]", "-", raw)


def promoted_server_identity(role: str) -> str | None:
    """Read the claimed promoted identity without loading model weights or hashing files."""

    if role not in ROLE_SETTINGS:
        raise KeyError(f"unknown SLM role: {role}")
    manifest_path = promoted_manifest_root() / ROLE_SETTINGS[role][0]
    if not manifest_path.is_file():
        return None
    try:
        manifest = AdapterManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
    if (
        manifest.target_roles != [role]
        or manifest.base_model_id != "google/gemma-3-1b-it"
        or manifest.format != "gguf-lora"
    ):
        return None
    return server_identity(role, manifest)


def validated_server_specs(settings: Settings) -> dict[str, SlmServerSpec]:
    specs: dict[str, SlmServerSpec] = {}
    for role, (manifest_name, endpoint_setting) in ROLE_SETTINGS.items():
        manifest_path = promoted_manifest_root() / manifest_name
        if not manifest_path.is_file():
            raise ValueError(
                f"promoted manifest is missing for {role}: {manifest_path}"
            )
        manifest = AdapterManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        if (
            manifest.target_roles != [role]
            or manifest.base_model_id != "google/gemma-3-1b-it"
            or manifest.format != "gguf-lora"
        ):
            raise ValueError(f"promoted manifest identity mismatch for {role}")
        manifest.verify(settings.gemma_base_model_path)
        endpoint_value = str(getattr(settings, endpoint_setting)).rstrip("/")
        endpoint = urlparse(endpoint_value)
        if endpoint.scheme != "http":
            raise ValueError(f"{role} endpoint must use HTTP on localhost")
        if endpoint.hostname not in {"127.0.0.1", "localhost"} or not endpoint.port:
            raise ValueError(f"{role} endpoint must be an explicit localhost port")
        identity = server_identity(role, manifest)
        command = (
            "llama-server",
            "--host",
            "127.0.0.1",
            "--port",
            str(endpoint.port),
            "--model",
            str(settings.gemma_base_model_path.resolve()),
            "--lora",
            str(manifest.adapter_path.resolve()),
            "--alias",
            identity,
            "--ctx-size",
            "4096",
        )
        specs[role] = SlmServerSpec(
            role=role,
            endpoint=endpoint_value,
            server_identity=identity,
            command=command,
        )
    endpoints = [spec.endpoint for spec in specs.values()]
    if len(endpoints) != len(set(endpoints)):
        raise ValueError("each promoted SLM requires a unique localhost endpoint")
    return specs


def validated_server_commands(settings: Settings) -> dict[str, list[str]]:
    """Backward-compatible command view used by dry preflight tooling."""

    return {
        role: list(spec.command)
        for role, spec in validated_server_specs(settings).items()
    }


def sanitized_server_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Pass only OS/GPU runtime variables; never forward application credentials."""

    if source is None:
        source = os.environ
    allowed = {
        "CUDA_PATH",
        "CUDA_VISIBLE_DEVICES",
        "HIP_PATH",
        "HOME",
        "LANG",
        "LD_LIBRARY_PATH",
        "LOCALAPPDATA",
        "PATH",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
    }
    return {key: value for key, value in source.items() if key.upper() in allowed}


async def _default_probe(spec: SlmServerSpec) -> ModelEndpointStatus:
    client = LlamaClient(
        spec.endpoint,
        timeout=1.0,
        expected_model_id=spec.server_identity,
    )
    return await client.probe()


def _stop_processes(processes: Mapping[str, Any]) -> None:
    for process in processes.values():
        if process.poll() is None:
            process.terminate()
    for process in processes.values():
        if process.poll() is not None:
            continue
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


async def supervise_servers(
    specs: Mapping[str, SlmServerSpec],
    *,
    startup_timeout_s: float = 45.0,
    poll_interval_s: float = 0.25,
    popen_factory: Callable[..., Any] = subprocess.Popen,
    readiness_probe: Callable[
        [SlmServerSpec], Awaitable[ModelEndpointStatus]
    ] = _default_probe,
) -> None:
    """Start all SLMs as one unit and tear the unit down if any member fails."""

    if not specs:
        raise ValueError("at least one SLM server specification is required")
    processes: dict[str, Any] = {}
    try:
        for role, spec in specs.items():
            processes[role] = popen_factory(
                list(spec.command),
                env=sanitized_server_environment(),
                stdin=subprocess.DEVNULL,
            )

        pending = set(specs)
        deadline = time.monotonic() + startup_timeout_s
        last_status: dict[str, ModelEndpointStatus] = {}
        while pending:
            failed = {
                role: process.returncode
                for role, process in processes.items()
                if process.poll() is not None
            }
            if failed:
                raise RuntimeError(f"SLM server exited during startup: {failed}")
            statuses = await asyncio.gather(
                *(readiness_probe(specs[role]) for role in sorted(pending))
            )
            for role, status in zip(sorted(pending), statuses, strict=True):
                last_status[role] = status
                if status.ready:
                    pending.discard(role)
            if pending and time.monotonic() >= deadline:
                failures = {role: last_status[role].error for role in sorted(pending)}
                raise TimeoutError(f"SLM servers did not become ready: {failures}")
            if pending:
                await asyncio.sleep(poll_interval_s)

        while True:
            failed = {
                role: process.returncode
                for role, process in processes.items()
                if process.poll() is not None
            }
            if failed:
                raise RuntimeError(f"SLM server exited unexpectedly: {failed}")
            await asyncio.sleep(poll_interval_s)
    finally:
        _stop_processes(processes)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate or launch promoted Gemma web SLM servers"
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="start and supervise the three verified localhost llama.cpp servers",
    )
    args = parser.parse_args()
    specs = validated_server_specs(Settings())
    if not args.start:
        print(
            json.dumps(
                {role: list(spec.command) for role, spec in specs.items()},
                indent=2,
            )
        )
        return
    asyncio.run(supervise_servers(specs))


if __name__ == "__main__":
    main()
