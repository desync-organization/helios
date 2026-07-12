# Helios Gemma web SLM training

This package defines three deliberately narrow, spawnable specialists:

| Runtime role | Student | Teacher | Boundary |
|---|---|---|---|
| `html-slm` | Gemma 3 1B IT | Gemma 3 4B IT | Semantic accessible HTML only |
| `css-slm` | Gemma 3 1B IT | Gemma 3 4B IT | Scoped responsive CSS only |
| `javascript-slm` | Gemma 3 1B IT | Gemma 3 4B IT | Safe browser JavaScript only |

They are adapters over one reviewed Gemma 3 1B base, not three uncontrolled full-model copies. The
4B model is an offline teacher: it creates traceable candidates which must pass deterministic language
checks and human/evaluation review before the 1B student sees them. It is never the runtime critic.

## Safety and reproducibility

The checked-in configuration never downloads a model implicitly: `localFilesOnly` is `true`, revisions
must be replaced with immutable reviewed commits, and training/distillation additionally require the
explicit `--execute` flag. Importing this package or inspecting/validating data does not import Torch,
Transformers, TRL, PEFT, Datasets, or BitsAndBytes.

QLoRA is the default recipe for a practical 1B training footprint. Set `method: lora` together with
`quantization: none` only on hardware that can train the unquantized base. Training never changes tool
grants, policy, agent availability, or critic independence.

## Workflow

From this directory, create a Python 3.12 environment and install the lightweight package:

```powershell
python -m pip install -e .
python -m helios_slm inspect configs/html.yaml
```

Install ML dependencies only on the training host:

```powershell
python -m pip install -e ".[train]"
```

Prepare consented source records without `response` and use a locally cached teacher to distill them:

```powershell
python -m helios_slm distill configs/html.yaml --source seed/html-train.jsonl --output datasets/html/train.jsonl --execute
```

Keep a separately curated validation split, then validate both and create the content-bound manifest:

```powershell
python -m helios_slm validate configs/html.yaml --manifest manifests/generated/html-dataset.json
```

Train only after deterministic validation, data review, and immutable model revisions are in place:

```powershell
python -m helios_slm train configs/html.yaml --execute
```

Repeat for CSS and JavaScript. Do not combine their datasets: narrow output boundaries are the point of
the specialists.

## Evaluation and promotion

Training output is not executable by Helios until it passes the independent held-out evaluator, is
converted to the runtime-supported adapter format when required, and receives a promotion manifest.
The evaluator must check at least syntax/parse success, output-boundary violations, accessibility for
HTML/CSS, browser tests for JavaScript, repository build integration, secret leakage, memorization, and
base-versus-adapter regression. The head orchestrator's critic then validates each produced artifact
at runtime; that critic must not use the producer's adapter.

Create a manifest only from real files:

```powershell
python -m helios_slm promote configs/html.yaml `
  --adapter outputs/html/gemma-html-lora.gguf `
  --base-model C:/models/gemma-3-1b-it/model.gguf `
  --tokenizer C:/models/gemma-3-1b-it/tokenizer.json `
  --dataset-manifest manifests/generated/html-dataset.json `
  --eval-report evals/reports/html.json `
  --training-run-id html-2026-07-12-001 `
  --output ../adapters/promoted/html-active.json
```

The training library saves PEFT/safetensors output first. Convert it with the reviewed llama.cpp LoRA
conversion workflow against the exact base revision; promotion deliberately rejects anything except a
`.gguf` adapter. The command hashes every input and emits the exact adapter contract consumed by Helios.
Promotion must remain a reviewed action; do not point the runtime at an unreviewed output directory.

## Runtime handoff

The role names and adapter IDs intentionally match the reservoir templates:
`html-slm/gemma-html-lora`, `css-slm/gemma-css-lora`, and
`javascript-slm/gemma-javascript-lora`. The orchestrator may discover and spawn these templates when a
plan requires the capability. The specialist returns a typed patch artifact, and an independent critic
checks its content hash, acceptance criteria, deterministic parser/build/test evidence, and safety gates
before an intent can be produced.
