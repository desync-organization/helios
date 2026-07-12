from pathlib import Path

from helios.workspace.repositories import safe_join


def read_repository_file(root: Path, relative_path: str, max_bytes: int = 256_000) -> str:
    path = safe_join(root, relative_path)
    if not path.is_file():
        raise FileNotFoundError(relative_path)
    if path.stat().st_size > max_bytes:
        raise ValueError("file exceeds read limit")
    return path.read_text(encoding="utf-8", errors="replace")

