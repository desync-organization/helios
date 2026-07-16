import asyncio
import hashlib
import os
import shutil
import sys
from contextlib import suppress
from pathlib import Path

import psutil
from pydantic import BaseModel

from helios.security.redaction import redact_text

from .repositories import safe_join


class CommandResult(BaseModel):
    argv: list[str]
    command_hash: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SafeCommandRunner:
    def __init__(self, root: Path, allowed_commands: set[str], output_cap: int = 32_000,
                 *, network_permitted: bool = False, state_root: Path | None = None) -> None:
        self.root = root.resolve()
        self.state_root = (state_root or root).resolve()
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.allowed_commands = allowed_commands
        self.output_cap = min(max(output_cap, 1_024), 64_000)
        self.network_permitted = network_permitted

    def _environment(self) -> dict[str, str]:
        home = safe_join(self.state_root, ".helios-home")
        temporary = safe_join(self.state_root, ".helios-tmp")
        home.mkdir(parents=True, exist_ok=True)
        temporary.mkdir(parents=True, exist_ok=True)
        runtime_bin = str(Path(sys.executable).resolve().parent)
        host_path = os.environ.get("PATH", "")
        command_path = os.pathsep.join(
            [runtime_bin, *[item for item in host_path.split(os.pathsep) if item != runtime_bin]]
        )
        environment = {
            "PATH": command_path,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NO_COLOR": "1",
            "CI": "1",
            "HOME": str(home),
            "USERPROFILE": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUNBUFFERED": "1",
            "TEMP": str(temporary),
            "TMP": str(temporary),
        }
        for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
            if os.environ.get(name):
                environment[name] = os.environ[name]
        if not self.network_permitted:
            # Package managers honor these settings. The command allowlist remains the
            # primary boundary; this prevents accidental dependency/network fallback.
            environment.update({
                "HTTP_PROXY": "http://127.0.0.1:9",
                "HTTPS_PROXY": "http://127.0.0.1:9",
                "ALL_PROXY": "http://127.0.0.1:9",
                "NO_PROXY": "",
                "NPM_CONFIG_OFFLINE": "true",
                "PIP_NO_INDEX": "1",
                "CARGO_NET_OFFLINE": "true",
            })
        return environment

    @staticmethod
    def _bounded_output(value: bytes, cap: int, truncated: bool = False) -> str:
        decoded = value.decode(errors="replace")
        if len(decoded) <= cap and not truncated:
            return decoded
        if truncated:
            return f"{decoded[:cap]}\n...[HELIOS OUTPUT TRUNCATED]..."
        head = cap // 2
        tail = cap - head
        return f"{decoded[:head]}\n...[HELIOS OUTPUT TRUNCATED]...\n{decoded[-tail:]}"

    async def _capture(self, stream: asyncio.StreamReader | None) -> tuple[bytes, bool]:
        if stream is None:
            return b"", False
        chunks: list[bytes] = []
        captured = 0
        truncated = False
        while True:
            chunk = await stream.read(8_192)
            if not chunk:
                break
            remaining = self.output_cap - captured
            if remaining > 0:
                chunks.append(chunk[:remaining])
                captured += min(len(chunk), remaining)
            if len(chunk) > remaining:
                truncated = True
        return b"".join(chunks), truncated

    @staticmethod
    def _kill_process_tree(process: asyncio.subprocess.Process) -> None:
        with suppress(psutil.Error):
            parent = psutil.Process(process.pid)
            descendants = parent.children(recursive=True)
            for child in descendants:
                with suppress(psutil.Error):
                    child.kill()
            parent.kill()
        with suppress(ProcessLookupError):
            process.kill()

    async def run(self, argv: list[str], *, cwd: str = ".", timeout: float = 60) -> CommandResult:
        if not argv or argv[0] not in self.allowed_commands:
            raise PermissionError("command is not allowlisted")
        executable = argv[0]
        environment = self._environment()
        resolved = (
            str(Path(executable).resolve())
            if Path(executable).is_file()
            else shutil.which(executable, path=environment["PATH"])
        )
        if resolved is None:
            raise FileNotFoundError(f"allowlisted executable is unavailable: {executable}")
        workdir = safe_join(self.root, cwd)
        if not workdir.is_dir():
            raise ValueError("working directory does not exist")
        process = await asyncio.create_subprocess_exec(
            resolved,
            *argv[1:],
            cwd=workdir,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_task = asyncio.create_task(self._capture(process.stdout))
        stderr_task = asyncio.create_task(self._capture(process.stderr))
        timed_out = False
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except TimeoutError:
            timed_out = True
            self._kill_process_tree(process)
            await process.wait()
        except asyncio.CancelledError:
            self._kill_process_tree(process)
            await process.wait()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise
        stdout_result, stderr_result = await asyncio.gather(stdout_task, stderr_task)
        stdout, stdout_truncated = stdout_result
        stderr, stderr_truncated = stderr_result
        return CommandResult(
            argv=argv,
            command_hash=hashlib.sha256("\0".join(argv).encode()).hexdigest(),
            exit_code=process.returncode if not timed_out else -1,
            stdout=redact_text(self._bounded_output(stdout, self.output_cap, stdout_truncated)),
            stderr=redact_text(self._bounded_output(stderr, self.output_cap, stderr_truncated)),
            timed_out=timed_out,
        )
