# Promoted adapters

Only independently evaluated, hash-bound GGUF LoRA manifests belong here:

- `html-active.json`
- `css-active.json`
- `javascript-active.json`

Generate them with `krishang/training` after training, held-out evaluation and GGUF conversion.
The runtime refuses model-backed specialist spawning when a manifest, base model or adapter hash does
not match. Model binaries and adapter weights remain untracked.

