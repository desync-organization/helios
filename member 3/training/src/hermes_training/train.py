"""Run a pinned, governed TRL LoRA/QLoRA supervised fine-tuning job."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hermes_training.environment import capture_environment, require_training_environment
from hermes_training.format_sft import format_record
from hermes_training.io import read_jsonl, write_json_atomic
from hermes_training.models import DatasetManifest, DatasetRecord
from hermes_training.run_artifacts import write_checksums, write_run_status
from hermes_training.training_config import TrainingConfig, load_training_config
from hermes_training.validate import validate_dataset


def preflight(config_path: Path, *, workspace: Path) -> dict[str, Any]:
    config, raw = load_training_config(config_path)
    manifest_path = config.dataset_manifest
    if not manifest_path.is_absolute():
        manifest_path = workspace / manifest_path
    count = validate_dataset(manifest_path, workspace=workspace)
    manifest = DatasetManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    return {
        "config": config,
        "configSha256": hashlib.sha256(raw).hexdigest(),
        "manifest": manifest,
        "manifestPath": manifest_path,
        "recordCount": count,
        "environment": capture_environment(),
    }


def _load_formatted_records(manifest: DatasetManifest, *, workspace: Path) -> list[dict[str, Any]]:
    dataset_path = Path(manifest.dataset_path)
    if not dataset_path.is_absolute():
        dataset_path = workspace / dataset_path
    records = [DatasetRecord.model_validate(item) for item in read_jsonl(dataset_path)]
    return [format_record(record) for record in records]


def run_training(config_path: Path, *, workspace: Path) -> Path:
    checked = preflight(config_path, workspace=workspace)
    config: TrainingConfig = checked["config"]
    environment = require_training_environment(compute_dtype=config.compute_dtype)
    started_at = datetime.now(UTC)
    run_id = f"{config.run_name}-{started_at:%Y%m%dT%H%M%SZ}-{checked['configSha256'][:8]}"
    output_root = config.output_root
    if not output_root.is_absolute():
        output_root = workspace / output_root
    run_root = output_root / run_id
    adapter_root = run_root / "adapter"
    run_root.mkdir(parents=True, exist_ok=False)
    write_run_status(run_root, status="running", details={"startedAt": started_at.isoformat()})
    try:
        import torch  # type: ignore[import-not-found]
        from peft import LoraConfig  # type: ignore[import-not-found]
        from transformers import BitsAndBytesConfig  # type: ignore[import-not-found]
        from trl import SFTConfig, SFTTrainer  # type: ignore[import-not-found]

        dataset_type = importlib.import_module("datasets").Dataset
        formatted = _load_formatted_records(checked["manifest"], workspace=workspace)
        train_dataset = dataset_type.from_list(
            [item for item in formatted if item["split"] == "train"]
        )
        dev_items = [item for item in formatted if item["split"] == "dev"]
        eval_dataset = dataset_type.from_list(dev_items) if dev_items else None
        dtype = torch.bfloat16 if config.compute_dtype == "bf16" else torch.float16
        quantization = None
        if config.method == "qlora":
            if config.quantization is None:
                raise RuntimeError("validated QLoRA config is missing quantization settings")
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=config.quantization.quant_type,
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_use_double_quant=config.quantization.double_quant,
            )
        lora = LoraConfig(
            r=config.lora.rank,
            lora_alpha=config.lora.alpha,
            lora_dropout=config.lora.dropout,
            target_modules=config.lora.target_modules,
            bias="none",
            task_type="CAUSAL_LM",
        )
        arguments = SFTConfig(
            output_dir=str(run_root / "checkpoints"),
            model_init_kwargs={
                "revision": config.base_model_revision,
                "dtype": dtype,
                "trust_remote_code": False,
            },
            num_train_epochs=config.training.epochs,
            learning_rate=config.training.learning_rate,
            max_length=config.training.max_length,
            per_device_train_batch_size=config.training.batch_size,
            gradient_accumulation_steps=config.training.gradient_accumulation_steps,
            warmup_ratio=config.training.warmup_ratio,
            weight_decay=config.training.weight_decay,
            logging_steps=config.training.logging_steps,
            seed=config.training.seed,
            data_seed=config.training.seed,
            packing=config.training.packing,
            assistant_only_loss=config.training.assistant_only_loss,
            eval_strategy="epoch" if eval_dataset is not None else "no",
            save_strategy="epoch",
            report_to="none",
        )
        trainer = SFTTrainer(
            model=config.base_model_id,
            args=arguments,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            quantization_config=quantization,
            peft_config=lora,
        )
        result = trainer.train()
        trainer.save_model(str(adapter_root))
        metrics = dict(result.metrics)
        if eval_dataset is not None:
            metrics.update({f"eval_{key}": value for key, value in trainer.evaluate().items()})
        write_json_atomic(run_root / "metrics.json", metrics)
        write_json_atomic(run_root / "environment.json", environment)
        write_json_atomic(
            run_root / "provenance.json",
            {
                "runId": run_id,
                "configPath": str(config_path),
                "configSha256": checked["configSha256"],
                "datasetManifestPath": str(checked["manifestPath"]),
                "datasetManifestSha256": checked["manifest"].manifest_sha256,
                "baseModelId": config.base_model_id,
                "baseModelRevision": config.base_model_revision,
                "baseModelSha256": config.base_model_sha256,
                "tokenizerSha256": config.tokenizer_sha256,
            },
        )
        write_run_status(
            run_root,
            status="complete",
            details={"finishedAt": datetime.now(UTC).isoformat()},
        )
        write_checksums(run_root)
        return run_root
    except Exception as error:
        write_run_status(
            run_root,
            status="failed",
            details={
                "finishedAt": datetime.now(UTC).isoformat(),
                "errorType": type(error).__name__,
                "message": str(error),
            },
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.preflight:
        checked = preflight(args.config, workspace=workspace)
        print(
            json.dumps(
                {
                    "configSha256": checked["configSha256"],
                    "recordCount": checked["recordCount"],
                    "manifestSha256": checked["manifest"].manifest_sha256,
                    "environment": checked["environment"],
                },
                indent=2,
            )
        )
        return
    print(run_training(args.config, workspace=workspace))


if __name__ == "__main__":
    main()
