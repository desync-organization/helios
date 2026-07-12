import time
from uuid import uuid4


_ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_PREFIXES = {
    "task": "tsk",
    "run": "run",
    "span": "spn",
    "artifact": "art",
    "event": "evt",
    "writeback": "wba",
    "plan": "pln",
    "lease": "lse",
}

def new_id(prefix: str) -> str:
    """Return a sortable domain ID compatible with the control-plane contracts."""
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    value = (timestamp_ms << 80) | (uuid4().int & ((1 << 80) - 1))
    encoded = ""
    for _ in range(26):
        encoded = _ENCODING[value & 31] + encoded
        value >>= 5
    return f"{_PREFIXES.get(prefix, prefix)}_{encoded}"

