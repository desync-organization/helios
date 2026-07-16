from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    role: str
    endpoint: str
    quantization: str
    estimated_vram_mb: int = Field(ge=0)
    hot: bool = False
    tier: str
    model_path: Path | None = None
    expected_server_id: str | None = None
    verify_identity: bool = False

    @property
    def physical_key(self) -> tuple[str, str]:
        """Identify one physical server allocation shared by one or more roles."""

        model_identity = (
            str(self.model_path.resolve()) if self.model_path else self.model_id
        )
        return self.endpoint.rstrip("/"), model_identity


def default_model_registry(settings: Any) -> dict[str, ModelDefinition]:
    from .slm import promoted_server_identity

    slm_identities = {
        role: promoted_server_identity(role)
        for role in ("html-slm", "css-slm", "javascript-slm")
    }
    return {
        "planner": ModelDefinition(
            model_id="qwen3-8b-q4",
            role="planner",
            endpoint=settings.llama_planner_url,
            quantization="Q4",
            estimated_vram_mb=4_800,
            hot=True,
            tier="local-8b",
            expected_server_id="qwen3-8b-q4",
            verify_identity=True,
        ),
        "critic": ModelDefinition(
            model_id="qwen3-8b-q4",
            role="critic",
            endpoint=settings.llama_planner_url,
            quantization="Q4",
            estimated_vram_mb=4_800,
            hot=True,
            tier="local-8b",
            expected_server_id="qwen3-8b-q4",
            verify_identity=True,
        ),
        "triage": ModelDefinition(
            model_id="qwen3-4b-q4",
            role="triage",
            endpoint=settings.llama_triage_url,
            quantization="Q4",
            estimated_vram_mb=2_800,
            tier="local-4b",
            expected_server_id="qwen3-4b-q4",
            verify_identity=True,
        ),
        "coder": ModelDefinition(
            model_id="qwen2.5-coder-7b-q4",
            role="coder",
            endpoint=settings.llama_coder_url,
            quantization="Q4-partial-offload",
            estimated_vram_mb=2_700,
            tier="local-coder-offload",
            expected_server_id="qwen2.5-coder-7b-q4",
            verify_identity=True,
        ),
        "embedding": ModelDefinition(
            model_id="bge-small",
            role="embedding",
            endpoint=settings.llama_embed_url,
            quantization="Q8",
            estimated_vram_mb=900,
            tier="local-embed",
            expected_server_id="bge-small",
            verify_identity=True,
        ),
        "html-slm": ModelDefinition(
            model_id="google/gemma-3-1b-it",
            role="html-slm",
            endpoint=settings.llama_html_slm_url,
            quantization="Q4",
            estimated_vram_mb=900,
            tier="local-slm",
            model_path=settings.gemma_base_model_path,
            expected_server_id=slm_identities["html-slm"],
            verify_identity=slm_identities["html-slm"] is not None,
        ),
        "css-slm": ModelDefinition(
            model_id="google/gemma-3-1b-it",
            role="css-slm",
            endpoint=settings.llama_css_slm_url,
            quantization="Q4",
            estimated_vram_mb=900,
            tier="local-slm",
            model_path=settings.gemma_base_model_path,
            expected_server_id=slm_identities["css-slm"],
            verify_identity=slm_identities["css-slm"] is not None,
        ),
        "javascript-slm": ModelDefinition(
            model_id="google/gemma-3-1b-it",
            role="javascript-slm",
            endpoint=settings.llama_javascript_slm_url,
            quantization="Q4",
            estimated_vram_mb=900,
            tier="local-slm",
            model_path=settings.gemma_base_model_path,
            expected_server_id=slm_identities["javascript-slm"],
            verify_identity=slm_identities["javascript-slm"] is not None,
        ),
    }
