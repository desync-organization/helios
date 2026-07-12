from pathlib import Path

from helios.workspace.commands import CommandResult, SafeCommandRunner


async def run_configured_scanner(root: Path, argv: list[str], timeout: float) -> CommandResult:
    runner = SafeCommandRunner(root, {"bandit", "gitleaks", "npm", "pip-audit", "semgrep", "trivy"})
    return await runner.run(argv, timeout=timeout)

