# Adapter Registry Handoff

Only metadata, checksums, model cards, and reviewed promotion pointers belong in Git. Large PEFT/GGUF
weights remain in the approved artifact store. A trained adapter is an experiment until all quality,
safety, compatibility, performance, three-run stability, activation, and rollback gates pass.

`promoted/active.json` is written only after Members 1 and 2 provide loader and atomic-registry evidence.
The independent Critic must never use the producer's adapter.

