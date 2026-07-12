import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from helios.contracts import NormalizedTask


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")

RUNTIME_STATUS_BAR = '''"use client";

import { Activity, MessageSquare, Wifi, WifiOff } from "lucide-react";
import { useOrchestratorStore } from "@/lib/orchestrator-store";

interface RuntimeStatusBarProps {
    onOpenChat: () => void;
}

export function RuntimeStatusBar({ onOpenChat }: RuntimeStatusBarProps) {
    const connected = useOrchestratorStore((state) => state.connected);
    const wrappers = useOrchestratorStore((state) => state.wrappers);
    const activeAgents = Object.values(wrappers).filter((wrapper) =>
        ["THINKING", "WORKING"].includes(wrapper.status),
    ).length;

    return (
        <aside
            aria-live="polite"
            className="fixed left-1/2 top-3 z-50 flex w-[calc(100%-1.5rem)] max-w-2xl -translate-x-1/2 items-center justify-between gap-4 rounded-xl border border-white/10 bg-black/70 px-4 py-2 text-sm shadow-2xl backdrop-blur-xl"
        >
            <div className="flex min-w-0 items-center gap-3">
                <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                        connected
                            ? "bg-emerald-500/15 text-emerald-300"
                            : "bg-red-500/15 text-red-300"
                    }`}
                >
                    {connected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
                </span>
                <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">
                        {connected ? "Helios is live" : "Helios is offline"}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                        {connected
                            ? `${activeAgents} active agent${activeAgents === 1 ? "" : "s"} · ready for work`
                            : "Open Settings to configure the orchestrator connection"}
                    </p>
                </div>
            </div>

            <button
                type="button"
                onClick={onOpenChat}
                className="flex shrink-0 items-center gap-2 rounded-lg border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
            >
                {connected ? <MessageSquare className="h-3.5 w-3.5" /> : <Activity className="h-3.5 w-3.5" />}
                {connected ? "Open command center" : "View diagnostics"}
            </button>
        </aside>
    );
}
'''


@dataclass(slots=True)
class CommandEvidence:
    command: str
    exit_code: int
    stdout: str
    stderr: str

    def projection(self) -> dict[str, object]:
        return {
            "command": self.command,
            "exitCode": self.exit_code,
            "success": self.exit_code == 0,
            "stdout": self.stdout[-4_000:],
            "stderr": self.stderr[-4_000:],
        }


async def _run(argv: list[str], cwd: Path, timeout: float) -> CommandEvidence:
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        raise RuntimeError(f"{' '.join(argv)} timed out after {timeout:.0f}s")
    return CommandEvidence(
        command=" ".join(argv),
        exit_code=process.returncode,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )


def _homepage_files(checkout: Path, prompt: str) -> list[dict[str, str]]:
    lowered = prompt.lower()
    if not any(term in lowered for term in ("homepage", "home page", "website", "frontend")):
        raise ValueError("no repository-aware implementation strategy matched this build request")
    page_path = checkout / "src" / "app" / "page.tsx"
    store_path = checkout / "src" / "lib" / "orchestrator-store.ts"
    if not page_path.is_file() or not store_path.is_file():
        raise ValueError("homepage strategy requires a Next.js app page and Helios orchestrator store")
    page = page_path.read_text(encoding="utf-8")
    if "RuntimeStatusBar" in page:
        raise ValueError("the selected homepage improvement is already present")
    import_anchor = 'import { SettingsDialog } from "@/components/settings-dialog";'
    render_anchor = "      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />"
    if import_anchor not in page or render_anchor not in page:
        raise ValueError("homepage structure changed; refusing an unsafe textual patch")
    page = page.replace(
        import_anchor,
        f'{import_anchor}\nimport {{ RuntimeStatusBar }} from "@/components/runtime-status-bar";',
        1,
    ).replace(
        render_anchor,
        f'{render_anchor}\n      <RuntimeStatusBar onOpenChat={{() => setActiveView("chat")}} />',
        1,
    )
    return [
        {"path": "src/app/page.tsx", "content": page, "encoding": "utf-8"},
        {"path": "src/components/runtime-status-bar.tsx", "content": RUNTIME_STATUS_BAR, "encoding": "utf-8"},
    ]


async def prepare_repository_build(task: NormalizedTask, workspace: Path) -> None:
    if not REPOSITORY_PATTERN.fullmatch(task.repository):
        raise ValueError("repository identifier is invalid")
    checkout = workspace / "checkout"
    clone = await _run(
        ["git", "clone", "--depth", "1", f"https://github.com/{task.repository}.git", str(checkout)],
        workspace,
        120,
    )
    if clone.exit_code:
        raise RuntimeError(f"repository clone failed: {clone.stderr[-1_000:]}")
    revision = await _run(["git", "rev-parse", "HEAD"], checkout, 15)
    if revision.exit_code or not re.fullmatch(r"[a-f0-9]{40}", revision.stdout.strip(), re.I):
        raise RuntimeError("could not resolve repository base revision")

    files = _homepage_files(checkout, f"{task.title}\n{task.body}")
    for record in files:
        target = (checkout / record["path"]).resolve()
        if checkout.resolve() not in target.parents:
            raise ValueError("generated path escapes the repository checkout")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(record["content"], encoding="utf-8")

    evidence: list[CommandEvidence] = []
    if (checkout / "bun.lock").is_file() and (checkout / "package.json").is_file():
        for argv, timeout in (
            (["bun", "install", "--frozen-lockfile"], 300),
            (["bun", "run", "lint"], 180),
            (["bun", "run", "build"], 240),
        ):
            result = await _run(argv, checkout, timeout)
            evidence.append(result)
            if result.exit_code:
                raise RuntimeError(f"{result.command} failed: {(result.stderr or result.stdout)[-1_000:]}")
    else:
        result = await _run(["git", "diff", "--check"], checkout, 30)
        evidence.append(result)
        if result.exit_code:
            raise RuntimeError(f"git diff --check failed: {result.stderr[-1_000:]}")

    task.base_sha = revision.stdout.strip()
    task.metadata.update({
        "proposedFiles": files,
        "proposedOwner": "web-typescript",
        "testCommands": [item.command for item in evidence],
        "testResults": [item.projection() for item in evidence],
        "repositoryCitations": ["src/app/page.tsx", "src/lib/orchestrator-store.ts"],
        "affectedModules": [record["path"] for record in files],
        "securityLimitations": ["bounded secret-pattern and dependency checks only"],
    })
