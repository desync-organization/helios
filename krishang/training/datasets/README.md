# Dataset placement

Place reviewed JSONL files at `html/{train,validation}.jsonl`, `css/{train,validation}.jsonl`, and
`javascript/{train,validation}.jsonl`. Files are intentionally absent from source control until their
license, consent, provenance, deduplication, and secret/PII reviews are complete.

Each line must satisfy `schemas/dataset-record.schema.json`. Training and validation IDs and exact
instruction/response pairs must be disjoint. With the supplied recipes, every response must carry a
Gemma 3 4B teacher trace whose hash exactly matches the response.

Do not train on private repositories, issue bodies, credentials, copied production code, generated
outputs that failed deterministic checks, or content without an explicit compatible license.
