"""Render validated records into deterministic chat-style SFT examples."""

from __future__ import annotations

import json
from typing import Any

from hermes_training.models import DatasetRecord


def format_record(record: DatasetRecord) -> dict[str, Any]:
    system = (
        "You are a bounded Hermes specialist. Return only the requested typed artifact, obey the "
        "provided policy context, and escalate instead of inventing permissions or material facts."
    )
    user = json.dumps(
        {
            "mode": record.mode,
            "taskType": record.task_type,
            "input": record.input,
            "policyContext": record.policy_context,
            "expectedArtifactType": record.expected_artifact_type,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    assistant = (
        record.target
        if isinstance(record.target, str)
        else json.dumps(record.target, ensure_ascii=False, sort_keys=True)
    )
    return {
        "exampleId": record.example_id,
        "split": record.split,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
    }
