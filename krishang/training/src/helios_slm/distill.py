from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import SpecialistSpec, require_pinned_models
from .dataset import DatasetRecord


def distill(spec: SpecialistSpec, source_path: Path, destination: Path) -> None:
    """Generate teacher responses locally. Teacher weights are never downloaded implicitly."""
    require_pinned_models(spec)
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "distillation dependencies are missing; install with `pip install -e .[train]`"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(
        spec.model.teacher_id,
        revision=spec.model.teacher_revision,
        local_files_only=spec.model.local_files_only,
        trust_remote_code=spec.model.trust_remote_code,
    )
    model = AutoModelForCausalLM.from_pretrained(
        spec.model.teacher_id,
        revision=spec.model.teacher_revision,
        local_files_only=spec.model.local_files_only,
        trust_remote_code=spec.model.trust_remote_code,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source_path.open("r", encoding="utf-8") as source, destination.open("w", encoding="utf-8") as target:
        for line_number, raw in enumerate(source, 1):
            payload = json.loads(raw)
            if payload.get("response"):
                raise ValueError(f"{source_path}:{line_number}: source must not contain a response")
            messages = [
                {"role": "system", "content": (
                    f"Act only as {spec.role}. Output the requested artifact with no markdown fence. "
                    f"Forbidden: {', '.join(spec.forbidden)}"
                )},
                {"role": "user", "content": payload["instruction"] + "\nContext:\n" + str(payload.get("context", {}))},
            ]
            encoded = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
            encoded = encoded.to(model.device)
            with torch.inference_mode():
                generated = model.generate(encoded, max_new_tokens=2048, do_sample=False)
            response = tokenizer.decode(generated[0, encoded.shape[-1]:], skip_special_tokens=True).strip()
            payload["schemaVersion"] = "1.0"
            payload["role"] = spec.role
            payload["response"] = response
            payload["teacher"] = {
                "modelId": spec.model.teacher_id,
                "modelRevision": spec.model.teacher_revision,
                "responseSha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
            }
            DatasetRecord.model_validate(payload)
            target.write(json.dumps(payload, sort_keys=True) + "\n")
