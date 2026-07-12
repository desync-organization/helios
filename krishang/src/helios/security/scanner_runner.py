import hashlib
from pathlib import Path

from helios.contracts.security import ScannerResult
from helios.security.redaction import redact_text
from helios.workspace.commands import SafeCommandRunner


async def run_scanner(root: Path, scanner: str, argv: list[str], *, version: str,
                      timeout: float, exclusions: list[str]) -> ScannerResult:
    result = await SafeCommandRunner(root, {scanner}).run(argv, timeout=timeout)
    output = redact_text((result.stdout + "\n" + result.stderr)[:32_000])
    output_ref = hashlib.sha256(output.encode()).hexdigest()
    return ScannerResult(scanner=scanner, scanner_version=version,
                         command_hash=result.command_hash, exclusions=exclusions,
                         exit_code=result.exit_code, output_ref=output_ref)

