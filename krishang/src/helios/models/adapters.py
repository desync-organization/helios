import json
from pathlib import Path

from helios.contracts.adapter import AdapterManifest


class AdapterLoader:
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self.active: AdapterManifest | None = None

    def load(self, base_model_path: Path) -> AdapterManifest:
        manifest = AdapterManifest.model_validate(json.loads(self.manifest_path.read_text(encoding="utf-8")))
        manifest.verify(base_model_path)
        self.active = manifest
        return manifest

    def for_role(self, role: str) -> AdapterManifest | None:
        return self.active if self.active and role in self.active.target_roles else None

    def for_critic(self, producer_adapter_id: str | None) -> AdapterManifest | None:
        if not self.active or self.active.adapter_id == producer_adapter_id:
            return None
        return self.active

    def rollback(self) -> None:
        self.active = None
