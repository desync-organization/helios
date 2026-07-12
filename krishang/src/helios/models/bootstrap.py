import json
from pathlib import Path
from typing import Any


def preflight(settings: Any | None = None) -> dict[str, Any]:
    if settings is None:
        return {"ready": True, "mode": "deterministic", "credentialsPresent": False,
                "checks": {"pythonPackage": True}}
    model_mode = settings.helios_inference_mode == "model"
    core_endpoints = all((settings.llama_planner_url, settings.llama_triage_url, settings.llama_coder_url))
    catalog = settings.helios_agent_catalog
    if not catalog.is_file():
        catalog = Path(__file__).resolve().parents[3] / "agents" / "baseline.yaml"
    manifest_root = catalog.resolve().parent.parent / "adapters" / "promoted"
    slm_manifests = {
        role: (manifest_root / f"{role}-active.json").is_file()
        for role in ("html", "css", "javascript")
    }
    checks = {
        "agentCatalog": catalog.is_file(),
        "coreModelEndpointsConfigured": core_endpoints,
        "gemmaBaseModel": settings.gemma_base_model_path.is_file(),
        "htmlAdapterManifest": slm_manifests["html"],
        "cssAdapterManifest": slm_manifests["css"],
        "javascriptAdapterManifest": slm_manifests["javascript"],
    }
    return {
        "ready": checks["agentCatalog"] and (not model_mode or core_endpoints),
        "mode": settings.helios_inference_mode,
        "credentialsPresent": False,
        "slmReady": checks["gemmaBaseModel"] and all(slm_manifests.values()),
        "checks": checks,
    }


def main() -> None:
    from helios.config import Settings
    print(json.dumps(preflight(Settings()), indent=2))


if __name__ == "__main__":
    main()
