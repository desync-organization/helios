from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    convex_http_url: str = ""
    helios_runtime_token: str = ""
    helios_instance_id: str = "demo-laptop-1"
    helios_api_host: str = "127.0.0.1"
    helios_api_port: int = 8788
    helios_local_api_token: str = "local-development-token"
    helios_allowed_origin: str = "http://127.0.0.1:3000"
    helios_workspace_root: Path = Path("./workspace")
    helios_outbox_path: Path = Path("./workspace/outbox.jsonl")
    helios_max_vram_mb: int = 7600
    helios_max_parallel_nodes: int = Field(3, ge=1, le=16)
    helios_fast_lane_timeout_s: float = 55
    helios_deep_lane_timeout_s: float = 480
    helios_security_scan_timeout_s: float = 600
    helios_writeback_mode: Literal["dry-run", "intent"] = "dry-run"
    helios_default_mode: Literal["maintain", "build", "security_audit"] = "maintain"
    llama_planner_url: str = "http://127.0.0.1:8081"
    llama_triage_url: str = "http://127.0.0.1:8082"
    llama_coder_url: str = "http://127.0.0.1:8083"
    llama_embed_url: str = "http://127.0.0.1:8084"
    llama_html_slm_url: str = "http://127.0.0.1:8085"
    llama_css_slm_url: str = "http://127.0.0.1:8086"
    llama_javascript_slm_url: str = "http://127.0.0.1:8087"
    helios_inference_mode: Literal["deterministic", "model"] = "deterministic"
    helios_fallback_url: str = "http://127.0.0.1:8787/inference/fallback"
    helios_adapter_manifest: Path = Path("./adapters/promoted/active.json")
    helios_agent_catalog: Path = Path("./agents/baseline.yaml")
    gemma_base_model_path: Path = Path("./models/gemma-3-1b-it-q4.gguf")
    git_repo_cache_root: Path = Path("./workspace/repos")

    def ensure_directories(self) -> None:
        self.helios_workspace_root.mkdir(parents=True, exist_ok=True)
        self.git_repo_cache_root.mkdir(parents=True, exist_ok=True)
        self.helios_outbox_path.parent.mkdir(parents=True, exist_ok=True)
