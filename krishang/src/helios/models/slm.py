import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from helios.config import Settings
from helios.contracts.adapter import AdapterManifest


ROLE_SETTINGS = {
    "html-slm": ("html-active.json", "llama_html_slm_url"),
    "css-slm": ("css-active.json", "llama_css_slm_url"),
    "javascript-slm": ("javascript-active.json", "llama_javascript_slm_url"),
}


def promoted_manifest_root() -> Path:
    return Path(__file__).resolve().parents[3] / "adapters" / "promoted"


def validated_server_commands(settings: Settings) -> dict[str, list[str]]:
    commands: dict[str, list[str]] = {}
    for role, (manifest_name, endpoint_setting) in ROLE_SETTINGS.items():
        manifest_path = promoted_manifest_root() / manifest_name
        if not manifest_path.is_file():
            raise ValueError(f"promoted manifest is missing for {role}: {manifest_path}")
        manifest = AdapterManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if role not in manifest.target_roles or manifest.base_model_id != "google/gemma-3-1b-it":
            raise ValueError(f"promoted manifest identity mismatch for {role}")
        manifest.verify(settings.gemma_base_model_path)
        endpoint = urlparse(str(getattr(settings, endpoint_setting)))
        if endpoint.hostname not in {"127.0.0.1", "localhost"} or not endpoint.port:
            raise ValueError(f"{role} endpoint must be an explicit localhost port")
        commands[role] = [
            "llama-server", "--host", "127.0.0.1", "--port", str(endpoint.port),
            "--model", str(settings.gemma_base_model_path.resolve()),
            "--lora", str(manifest.adapter_path.resolve()), "--ctx-size", "4096",
        ]
    return commands


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or launch promoted Gemma web SLM servers")
    parser.add_argument("--start", action="store_true", help="start the three verified localhost llama.cpp servers")
    args = parser.parse_args()
    commands = validated_server_commands(Settings())
    if not args.start:
        print(json.dumps(commands, indent=2))
        return
    processes = [subprocess.Popen(command) for command in commands.values()]
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()


if __name__ == "__main__":
    main()

