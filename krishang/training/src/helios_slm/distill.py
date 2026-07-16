from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import SpecialistSpec, require_pinned_models
from .dataset import DatasetRecord


def distill(spec: SpecialistSpec, source_path: Path, destination: Path) -> None:
    """Generate text examples with the pinned multimodal Gemma 3 teacher."""

    require_pinned_models(spec)
    try:
        import torch
        from transformers import AutoProcessor, Gemma3ForConditionalGeneration
    except ImportError as exc:
        raise RuntimeError(
            "distillation dependencies are missing; install with `pip install -e .[train]`"
        ) from exc

    processor = AutoProcessor.from_pretrained(
        spec.model.teacher_id,
        revision=spec.model.teacher_revision,
        local_files_only=spec.model.local_files_only,
        trust_remote_code=spec.model.trust_remote_code,
    )
    model = Gemma3ForConditionalGeneration.from_pretrained(
        spec.model.teacher_id,
        revision=spec.model.teacher_revision,
        local_files_only=spec.model.local_files_only,
        trust_remote_code=spec.model.trust_remote_code,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    ).eval()
    _validate_loaded_teacher(spec, model)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        source_path.open("r", encoding="utf-8") as source,
        destination.open("w", encoding="utf-8") as target,
    ):
        for line_number, raw in enumerate(source, 1):
            payload = json.loads(raw)
            if payload.get("response"):
                raise ValueError(
                    f"{source_path}:{line_number}: source must not contain a response"
                )
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Act only as {spec.role}. Output the requested artifact with no "
                                f"markdown fence. Forbidden: {', '.join(spec.forbidden)}"
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                payload["instruction"]
                                + "\nContext:\n"
                                + str(payload.get("context", {}))
                            ),
                        }
                    ],
                },
            ]
            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(model.device)
            input_length = inputs["input_ids"].shape[-1]
            with torch.inference_mode():
                generated = model.generate(
                    **inputs,
                    max_new_tokens=2048,
                    do_sample=False,
                )
            response = processor.decode(
                generated[0][input_length:],
                skip_special_tokens=True,
            ).strip()
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


def _validate_loaded_teacher(spec: SpecialistSpec, model: object) -> None:
    config = getattr(model, "config", None)
    if getattr(config, "model_type", None) != "gemma3":
        raise RuntimeError("loaded teacher is not a Gemma 3 model")
    configured_name = getattr(config, "_name_or_path", None)
    if configured_name and configured_name != spec.model.teacher_id:
        raise RuntimeError("loaded teacher identity does not match the specification")
    commit_hash = getattr(config, "_commit_hash", None)
    if commit_hash and commit_hash != spec.model.teacher_revision:
        raise RuntimeError("loaded teacher revision does not match the specification")
