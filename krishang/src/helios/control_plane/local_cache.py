import json
from pathlib import Path
from typing import Any


class LocalRunCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, state: dict[str, Any]) -> None:
        target = self.root / f"{run_id}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, sort_keys=True, default=str), encoding="utf-8")
        temporary.replace(target)

    def load(self, run_id: str) -> dict[str, Any] | None:
        target = self.root / f"{run_id}.json"
        return json.loads(target.read_text(encoding="utf-8")) if target.exists() else None

