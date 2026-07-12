# Evidence Index

This directory intentionally contains no claimed live completion. Populate a reviewed index during
merged-system acceptance with exact task/run IDs, external URLs, capture time, commit SHA, model,
adapter, prompt, policy, dataset, and case-set versions. Validate it with:

```powershell
python evidence/validate_index.py evidence/index.json
```

Fixtures, rehearsals, and fallback replays must retain their `dataClass` and set
`countsAsCompletion: false`. Redact private content and raw findings before capture.
