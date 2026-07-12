from typing import Any

import psutil


def memory_snapshot() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    return {
        "systemTotalMb": memory.total // (1024 * 1024),
        "systemAvailableMb": memory.available // (1024 * 1024),
        "gpu": "not-probed",
    }
