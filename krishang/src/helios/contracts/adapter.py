import hashlib
from pathlib import Path

from .common import WireModel


class LoraConfig(WireModel):
    rank: int
    alpha: float
    dropout: float
    target_modules: list[str]


class AdapterManifest(WireModel):
    adapter_id: str
    adapter_version: str
    adapter_sha256: str
    adapter_path: Path
    format: str
    base_model_id: str
    base_model_revision: str
    base_model_sha256: str
    tokenizer_sha256: str
    target_roles: list[str]
    training_run_id: str
    dataset_manifest_sha256: str
    lora: LoraConfig
    quantization: str
    eval_report_sha256: str
    promoted_at: str

    def verify(self, base_model_path: Path, adapter_path: Path | None = None) -> None:
        adapter = adapter_path or self.adapter_path
        for path, expected, label in (
            (base_model_path, self.base_model_sha256, "base model"),
            (adapter, self.adapter_sha256, "adapter"),
        ):
            if not path.is_file():
                raise ValueError(f"{label} file is missing: {path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != expected:
                raise ValueError(f"{label} hash mismatch")
