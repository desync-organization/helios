import asyncio
import hashlib
import os
from pathlib import Path

from pydantic import BaseModel

from .repositories import safe_join


class CommandResult(BaseModel):
    argv: list[str]
    command_hash: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SafeCommandRunner:
    def __init__(self, root: Path, allowed_commands: set[str], output_cap: int = 32_000) -> None:
        self.root = root.resolve()
        self.allowed_commands = allowed_commands
        self.output_cap = output_cap

    async def run(self, argv: list[str], *, cwd: str = ".", timeout: float = 60) -> CommandResult:
        if not argv or argv[0] not in self.allowed_commands:
            raise PermissionError("command is not allowlisted")
        workdir = safe_join(self.root, cwd)
        if not workdir.is_dir():
            raise ValueError("working directory does not exist")
        env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "NO_COLOR": "1"}
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=workdir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timed_out = False
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except TimeoutError:
            timed_out = True
            process.kill()
            stdout, stderr = await process.communicate()
        return CommandResult(
            argv=argv,
            command_hash=hashlib.sha256("\0".join(argv).encode()).hexdigest(),
            exit_code=process.returncode if not timed_out else -1,
            stdout=stdout.decode(errors="replace")[: self.output_cap],
            stderr=stderr.decode(errors="replace")[: self.output_cap],
            timed_out=timed_out,
        )

