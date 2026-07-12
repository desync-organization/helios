from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import SpecialistSpec, require_pinned_models
from .dataset import DatasetRecord, validate_pair


def training_plan(spec: SpecialistSpec, config_path: Path) -> dict[str, Any]:
    root = config_path.parent
    return {
        "role": spec.role,
        "student": spec.model.student_id,
        "teacher": spec.model.teacher_id,
        "method": spec.adapter.method,
        "adapterId": spec.adapter.adapter_id,
        "trainPath": str((root / spec.data.train_path).resolve()),
        "validationPath": str((root / spec.data.validation_path).resolve()),
        "outputDir": str((root / spec.training.output_dir).resolve()),
        "localFilesOnly": spec.model.local_files_only,
    }


def _to_text(record: DatasetRecord, tokenizer: Any) -> str:
    messages = [
        {"role": "system", "content": f"You are the bounded Helios {record.role} specialist."},
        {"role": "user", "content": record.instruction + "\nContext:\n" + str(record.context)},
        {"role": "assistant", "content": record.response},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)


def run_training(spec: SpecialistSpec, config_path: Path) -> Path:
    """Run supervised adapter training. Heavy ML dependencies are imported only here."""
    require_pinned_models(spec)
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        raise RuntimeError(
            "training dependencies are missing; install with `pip install -e .[train]`"
        ) from exc

    root = config_path.parent
    train, validation = validate_pair(
        root / spec.data.train_path,
        root / spec.data.validation_path,
        role=spec.role,
        require_teacher=spec.data.require_teacher_trace,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        spec.model.student_id,
        revision=spec.model.student_revision,
        local_files_only=spec.model.local_files_only,
        trust_remote_code=spec.model.trust_remote_code,
    )
    quantization_config = None
    if spec.adapter.method == "qlora":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        spec.model.student_id,
        revision=spec.model.student_revision,
        local_files_only=spec.model.local_files_only,
        trust_remote_code=spec.model.trust_remote_code,
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    if quantization_config:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=spec.training.gradient_checkpointing)
    peft_config = LoraConfig(
        r=spec.adapter.rank,
        lora_alpha=spec.adapter.alpha,
        lora_dropout=spec.adapter.dropout,
        target_modules=spec.adapter.target_modules,
        task_type="CAUSAL_LM",
        bias="none",
    )
    train_dataset = Dataset.from_dict({"text": [_to_text(item, tokenizer) for item in train]})
    eval_dataset = Dataset.from_dict({"text": [_to_text(item, tokenizer) for item in validation]})
    output_dir = (root / spec.training.output_dir).resolve()
    arguments = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=spec.training.epochs,
        learning_rate=spec.training.learning_rate,
        warmup_ratio=spec.training.warmup_ratio,
        per_device_train_batch_size=spec.training.per_device_train_batch_size,
        gradient_accumulation_steps=spec.training.gradient_accumulation_steps,
        gradient_checkpointing=spec.training.gradient_checkpointing,
        bf16=spec.training.bf16,
        save_steps=spec.training.save_steps,
        eval_steps=spec.training.eval_steps,
        logging_steps=spec.training.logging_steps,
        eval_strategy="steps",
        dataset_text_field="text",
        max_length=spec.data.max_sequence_length,
        seed=spec.training.seed,
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        args=arguments,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    return output_dir
