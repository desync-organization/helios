import asyncio
import json
import tempfile
from pathlib import Path

from helios.config import Settings
from helios.control_plane import InMemoryControlPlane
from helios.demo.fixtures import demo_tasks
from helios.runtime import HeliosRuntime


async def seed() -> dict:
    with tempfile.TemporaryDirectory(prefix="helios-demo-") as directory:
        settings = Settings(helios_workspace_root=Path(directory), git_repo_cache_root=Path(directory) / "repos",
                            helios_outbox_path=Path(directory) / "outbox.jsonl")
        control = InMemoryControlPlane()
        runtime = HeliosRuntime(settings, control)
        for task in demo_tasks():
            await control.enqueue(task)
        while await runtime.process_once():
            pass
        return {"runs": len(control.results), "artifacts": len(control.artifacts),
                "intents": [item.content for item in control.intents.values()], "events": len(control.events)}


def main() -> None:
    print(json.dumps(asyncio.run(seed()), indent=2))


if __name__ == "__main__":
    main()

