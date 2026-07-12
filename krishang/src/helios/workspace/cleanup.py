import shutil
from pathlib import Path


def cleanup_namespace(path: Path, workspace_root: Path) -> None:
    path = path.resolve()
    root = workspace_root.resolve()
    if root not in path.parents:
        raise ValueError("refusing to clean outside workspace")
    shutil.rmtree(path, ignore_errors=True)

