# Evaluation and Report Reproduction

Run the same frozen case-set hash and seed for `agents-v1` through `agents-v4`. Member 1 supplies one
result per case; `python -m hermes_evals.runner --cases ... --results ... --output ...` applies hard
checks before any qualitative rubric. A secret leak, unauthorized action, failed objective check, case
mismatch, or threshold regression returns a failing process status.

Reports keep actual local/provider cost separate from cloud-equivalent estimates. Any dataset, prompt,
policy, adapter, model, or case-set change invalidates final runs and requires three reruns.

