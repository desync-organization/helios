from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from .client import LlamaClient, ModelEndpointStatus
from .registry import ModelDefinition, default_model_registry
from .slm import ROLE_SETTINGS, promoted_manifest_root, validated_server_specs


CORE_MODEL_ROLES = ("planner", "triage", "coder", "embedding")


def _catalog_path(settings: Any) -> Path:
    catalog = settings.helios_agent_catalog
    if not catalog.is_file():
        catalog = Path(__file__).resolve().parents[3] / "agents" / "baseline.yaml"
    return catalog


def preflight(settings: Any | None = None) -> dict[str, Any]:
    """Perform filesystem/configuration checks without network or model loading."""

    if settings is None:
        return {
            "ready": True,
            "mode": "deterministic",
            "credentialsPresent": False,
            "checks": {"pythonPackage": True},
        }
    model_mode = settings.helios_inference_mode == "model"
    registry = default_model_registry(settings)
    core_endpoints = all(registry[role].endpoint for role in CORE_MODEL_ROLES)
    catalog = _catalog_path(settings)
    manifest_root = promoted_manifest_root()
    slm_manifests = {
        role: (manifest_root / manifest_name).is_file()
        for role, (manifest_name, _) in ROLE_SETTINGS.items()
    }
    checks = {
        "agentCatalog": catalog.is_file(),
        "coreModelEndpointsConfigured": core_endpoints,
        "liveModelIdentityVerified": not model_mode,
        "gemmaBaseModel": settings.gemma_base_model_path.is_file(),
        "htmlAdapterManifest": slm_manifests["html-slm"],
        "cssAdapterManifest": slm_manifests["css-slm"],
        "javascriptAdapterManifest": slm_manifests["javascript-slm"],
    }
    static_slm_ready = checks["gemmaBaseModel"] and all(slm_manifests.values())
    return {
        "ready": checks["agentCatalog"] and not model_mode,
        "mode": settings.helios_inference_mode,
        "credentialsPresent": False,
        "slmReady": static_slm_ready and not model_mode,
        "checks": checks,
    }


async def runtime_preflight(
    settings: Any,
    registry: Mapping[str, ModelDefinition] | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 1.5,
) -> dict[str, Any]:
    """Add live, exact-identity probes when model-backed inference is enabled."""

    result = preflight(settings)
    if settings.helios_inference_mode != "model":
        return result

    definitions = dict(registry or default_model_registry(settings))
    missing_roles = [role for role in CORE_MODEL_ROLES if role not in definitions]
    if missing_roles:
        result["checks"]["liveModelIdentityVerified"] = False
        result["checks"]["missingModelRoles"] = missing_roles
        result["ready"] = False
        return result

    core_statuses = await asyncio.gather(
        *(
            _probe(
                definitions[role].endpoint,
                definitions[role].model_id,
                timeout=timeout,
                transport=transport,
            )
            for role in CORE_MODEL_ROLES
        )
    )
    endpoint_probes = {
        role: status.model_dump(mode="json")
        for role, status in zip(CORE_MODEL_ROLES, core_statuses, strict=True)
    }
    core_ready = all(status.ready for status in core_statuses)

    slm_ready = False
    if result["checks"]["gemmaBaseModel"] and all(
        result["checks"][key]
        for key in (
            "htmlAdapterManifest",
            "cssAdapterManifest",
            "javascriptAdapterManifest",
        )
    ):
        try:
            specs = validated_server_specs(settings)
        except (OSError, ValueError) as exc:
            result["checks"]["slmManifestValidation"] = str(exc)
        else:
            roles = tuple(ROLE_SETTINGS)
            slm_statuses = await asyncio.gather(
                *(
                    _probe(
                        specs[role].endpoint,
                        specs[role].server_identity,
                        timeout=timeout,
                        transport=transport,
                    )
                    for role in roles
                )
            )
            endpoint_probes.update(
                {
                    role: status.model_dump(mode="json")
                    for role, status in zip(roles, slm_statuses, strict=True)
                }
            )
            slm_ready = all(status.ready for status in slm_statuses)

    result["endpointProbes"] = endpoint_probes
    result["checks"]["liveModelIdentityVerified"] = core_ready and slm_ready
    result["slmReady"] = slm_ready
    result["ready"] = result["checks"]["agentCatalog"] and core_ready and slm_ready
    return result


async def _probe(
    endpoint: str,
    expected_model_id: str,
    *,
    timeout: float,
    transport: httpx.AsyncBaseTransport | None,
) -> ModelEndpointStatus:
    return await LlamaClient(
        endpoint,
        timeout=timeout,
        expected_model_id=expected_model_id,
        transport=transport,
    ).probe()


def main() -> None:
    from helios.config import Settings

    print(json.dumps(asyncio.run(runtime_preflight(Settings())), indent=2))


if __name__ == "__main__":
    main()
