from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_spec
from .dataset import validate_pair, write_manifest
from .distill import distill
from .promotion import create_promotion_manifest
from .training import run_training, training_plan


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="helios-slm", description="Helios web SLM training tools")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="validate and print a training plan without loading ML libraries")
    inspect.add_argument("config", type=Path)
    validate = commands.add_parser("validate", help="validate train/validation data and write a dataset manifest")
    validate.add_argument("config", type=Path)
    validate.add_argument("--manifest", type=Path, required=True)
    train = commands.add_parser("train", help="execute adapter training; may load local model weights")
    train.add_argument("config", type=Path)
    train.add_argument("--execute", action="store_true", help="required safety confirmation")
    teacher = commands.add_parser("distill", help="generate examples with the configured local teacher")
    teacher.add_argument("config", type=Path)
    teacher.add_argument("--source", type=Path, required=True)
    teacher.add_argument("--output", type=Path, required=True)
    teacher.add_argument("--execute", action="store_true", help="required safety confirmation")
    promote = commands.add_parser("promote", help="create a hash-bound runtime adapter manifest")
    promote.add_argument("config", type=Path)
    promote.add_argument("--adapter", type=Path, required=True)
    promote.add_argument("--base-model", type=Path, required=True)
    promote.add_argument("--tokenizer", type=Path, required=True)
    promote.add_argument("--dataset-manifest", type=Path, required=True)
    promote.add_argument("--eval-report", type=Path, required=True)
    promote.add_argument("--training-run-id", required=True)
    promote.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    spec = load_spec(args.config)
    if args.command == "inspect":
        print(json.dumps(training_plan(spec, args.config), indent=2, sort_keys=True))
    elif args.command == "validate":
        root = args.config.parent
        paths = [root / spec.data.train_path, root / spec.data.validation_path]
        validate_pair(*paths, role=spec.role, require_teacher=spec.data.require_teacher_trace)
        print(json.dumps(write_manifest(paths, args.manifest), indent=2, sort_keys=True))
    elif args.command == "train":
        if not args.execute:
            raise SystemExit("refusing to load weights or train without --execute")
        print(run_training(spec, args.config))
    elif args.command == "distill":
        if not args.execute:
            raise SystemExit("refusing to load teacher weights without --execute")
        distill(spec, args.source, args.output)
    elif args.command == "promote":
        payload = create_promotion_manifest(
            spec,
            adapter_path=args.adapter,
            base_model_path=args.base_model,
            tokenizer_path=args.tokenizer,
            dataset_manifest_path=args.dataset_manifest,
            eval_report_path=args.eval_report,
            training_run_id=args.training_run_id,
            destination=args.output,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
