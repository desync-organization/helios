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


def default_model_registry(settings: Any) -> dict[str, ModelDefinition]:
    return {
        "planner": ModelDefinition(model_id="qwen3-8b-q4", role="planner", endpoint=settings.llama_planner_url, quantization="Q4", estimated_vram_mb=4_800, hot=True, tier="local-8b"),
        "critic": ModelDefinition(model_id="qwen3-8b-q4", role="critic", endpoint=settings.llama_planner_url, quantization="Q4", estimated_vram_mb=4_800, hot=True, tier="local-8b"),
        "triage": ModelDefinition(model_id="qwen3-4b-q4", role="triage", endpoint=settings.llama_triage_url, quantization="Q4", estimated_vram_mb=2_800, hot=True, tier="local-4b"),
        "coder": ModelDefinition(model_id="qwen2.5-coder-7b-q4", role="coder", endpoint=settings.llama_coder_url, quantization="Q4-partial-offload", estimated_vram_mb=2_700, tier="local-coder-offload"),
        "embedding": ModelDefinition(model_id="bge-small", role="embedding", endpoint=settings.llama_embed_url, quantization="Q8", estimated_vram_mb=900, hot=True, tier="local-embed"),
        "html-slm": ModelDefinition(model_id="google/gemma-3-1b-it", role="html-slm", endpoint=settings.llama_html_slm_url, quantization="Q4", estimated_vram_mb=900, tier="local-slm", model_path=settings.gemma_base_model_path),
        "css-slm": ModelDefinition(model_id="google/gemma-3-1b-it", role="css-slm", endpoint=settings.llama_css_slm_url, quantization="Q4", estimated_vram_mb=900, tier="local-slm", model_path=settings.gemma_base_model_path),
        "javascript-slm": ModelDefinition(model_id="google/gemma-3-1b-it", role="javascript-slm", endpoint=settings.llama_javascript_slm_url, quantization="Q4", estimated_vram_mb=900, tier="local-slm", model_path=settings.gemma_base_model_path),
    }
