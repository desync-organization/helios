"""Bounded connection registry and ordered event broadcaster."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from fastapi import WebSocket

from hermes_gateway.models import CanonicalEvent
from hermes_gateway.projection import canonical_message, direct_message


@dataclass(eq=False, slots=True)
class Connection:
    websocket: WebSocket
    format: Literal["direct", "canonical"]
    read_only: bool
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send_event(self, event: CanonicalEvent) -> None:
        message = canonical_message(event) if self.format == "canonical" else direct_message(event)
        async with self.send_lock:
            await self.websocket.send_json(message)


class EventHub:
    def __init__(self, buffer_size: int) -> None:
        self._connections: set[Connection] = set()
        self._buffer: deque[CanonicalEvent] = deque(maxlen=buffer_size)
        self._last_sequence_by_run: dict[str, int] = {}

    def add(self, connection: Connection) -> None:
        self._connections.add(connection)

    def remove(self, connection: Connection) -> None:
        self._connections.discard(connection)

    def sequence_gap(self, event: CanonicalEvent) -> bool:
        if not event.run_id:
            return False
        previous = self._last_sequence_by_run.get(event.run_id)
        return previous is not None and event.sequence > previous + 1

    async def publish(self, event: CanonicalEvent) -> None:
        if event.run_id:
            previous = self._last_sequence_by_run.get(event.run_id, -1)
            if event.sequence <= previous:
                return
            self._last_sequence_by_run[event.run_id] = event.sequence
        if any(buffered.event_id == event.event_id for buffered in self._buffer):
            return
        self._buffer.append(event)
        failed: list[Connection] = []
        for connection in tuple(self._connections):
            try:
                await connection.send_event(event)
            except RuntimeError:
                failed.append(connection)
        for connection in failed:
            self.remove(connection)
