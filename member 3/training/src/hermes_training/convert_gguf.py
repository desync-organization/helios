"""Convert a verified PEFT adapter with llama.cpp's official conversion utility."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from hermes_training.hashing import sha256_file
from hermes_training.io import write_json_atomic


def convert_adapter(
    *,
    adapter: Path,
    converter: Path,
    output: Path,
    base: Path | None,
    base_model_id: str | None,
    timeout_seconds: int = 1800,
) -> Path:
    if (base is None) == (base_model_id is None):
        raise ValueError("provide exactly one of base or base_model_id")
    if not converter.is_file() or converter.name != "convert_lora_to_gguf.py":
        raise FileNotFoundError("official llama.cpp convert_lora_to_gguf.py was not found")
    if not (adapter / "adapter_config.json").is_file():
        raise FileNotFoundError("adapter_config.json is required")
    command = [
        sys.executable,
        str(converter),
        "--outfile",
        str(output),
        "--outtype",
        "f16",
    ]
    if base is not None:
        command.extend(["--base", str(base)])
    else:
        command.extend(["--base-model-id", str(base_model_id)])
    command.append(str(adapter))
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"llama.cpp adapter conversion failed with exit code {completed.returncode}"
        )
    if not output.is_file():
        raise RuntimeError("llama.cpp reported success without producing an adapter")
    write_json_atomic(
        output.with_suffix(output.suffix + ".manifest.json"),
        {"format": "gguf-lora", "sha256": sha256_file(output), "path": str(output)},
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--converter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--base", type=Path)
    group.add_argument("--base-model-id")
    args = parser.parse_args()
    print(
        convert_adapter(
            adapter=args.adapter.resolve(),
            converter=args.converter.resolve(),
            output=args.output.resolve(),
            base=args.base.resolve() if args.base else None,
            base_model_id=args.base_model_id,
        )
    )


if __name__ == "__main__":
    main()

