import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any


class IdempotentOutbox:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def append(self, record_id: str, kind: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"id": record_id, "kind": kind, "payload": payload}, default=str) + "\n")

    async def replay(self, sender: Callable[[dict[str, Any]], Awaitable[None]]) -> int:
        if not self.path.exists():
            return 0
        async with self._lock:
            records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]
            sent: set[str] = set()
            for record in records:
                if record["id"] in sent:
                    continue
                await sender(record)
                sent.add(record["id"])
            self.path.write_text("", encoding="utf-8")
            return len(sent)

