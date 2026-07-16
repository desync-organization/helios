import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any


class IdempotentOutbox:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.dead_letter_path = self.path.with_suffix(".deadletter.jsonl")
        self._lock = asyncio.Lock()

    async def append(self, record_id: str, kind: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"id": record_id, "kind": kind, "payload": payload}, default=str) + "\n")

    async def replay(self, sender: Callable[[dict[str, Any]], Awaitable[None]]) -> int:
        if not self.path.exists():
            return 0
        async with self._lock:
            records: list[dict[str, Any]] = []
            malformed: list[dict[str, Any]] = []
            for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                        raise ValueError("record must be an object with a string id")
                    records.append(record)
                except (json.JSONDecodeError, ValueError) as exc:
                    malformed.append({"line": line_number, "error": str(exc)[:500], "raw": line[:8_192]})
            if malformed:
                with self.dead_letter_path.open("a", encoding="utf-8") as handle:
                    for record in malformed:
                        handle.write(json.dumps(record, default=str) + "\n")
            sent: set[str] = set()
            remaining: list[dict[str, Any]] = []
            for index, record in enumerate(records):
                if record["id"] in sent:
                    continue
                try:
                    await sender(record)
                except Exception:
                    remaining = [record, *records[index + 1:]]
                    break
                sent.add(record["id"])
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                "".join(json.dumps(record, default=str) + "\n" for record in remaining),
                encoding="utf-8",
            )
            temporary.replace(self.path)
            return len(sent)
