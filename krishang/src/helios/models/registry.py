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


def default_model_registry(settings: Any) -> dict[str, ModelDefinition]:
    return {
        "planner": ModelDefinition(model_id="qwen3-planner", role="planner", endpoint=settings.llama_planner_url, quantization="Q4", estimated_vram_mb=4_800, hot=True, tier="local-8b"),
        "critic": ModelDefinition(model_id="qwen3-critic", role="critic", endpoint=settings.llama_planner_url, quantization="Q4", estimated_vram_mb=4_800, hot=True, tier="local-8b"),
        "triage": ModelDefinition(model_id="qwen3-triage", role="triage", endpoint=settings.llama_triage_url, quantization="Q4", estimated_vram_mb=2_800, hot=True, tier="local-4b"),
        "coder": ModelDefinition(model_id="qwen-coder", role="coder", endpoint=settings.llama_coder_url, quantization="Q4", estimated_vram_mb=4_800, tier="local-coder"),
        "embedding": ModelDefinition(model_id="qwen-embedding", role="embedding", endpoint=settings.llama_embed_url, quantization="Q8", estimated_vram_mb=900, hot=True, tier="local-embed"),
    }
