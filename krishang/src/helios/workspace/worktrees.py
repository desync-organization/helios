import asyncio
from pathlib import Path

from .repositories import safe_join


async def create_worktree(repo: Path, workspace_root: Path, task_id: str, base_sha: str) -> Path:
    target = safe_join(workspace_root, "worktrees", task_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    process = await asyncio.create_subprocess_exec(
        "git", "-C", str(repo.resolve()), "worktree", "add", "--detach", str(target), base_sha,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode:
        raise RuntimeError(f"worktree creation failed: {stderr.decode(errors='replace')[:1000]}")
    return target

