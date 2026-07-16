from pathlib import Path

from helios.contracts import NormalizedTask


async def prepare_repository_build(task: NormalizedTask, workspace: Path) -> None:
    """Materialize the exact authorized repository revision for later specialists.

    This compatibility entry point intentionally performs no product-specific code
    generation and does not run tests before agent output exists. All implementation,
    integration, test, and scan evidence is produced by node-scoped execution services.
    """
    # Delayed to keep the workspace primitives usable while execution services
    # themselves import the safe command and path helpers.
    from helios.execution import ExecutionServices

    services = ExecutionServices(task, workspace)
    evidence = await services.materialize_repository()
    task.metadata["repositoryMaterialization"] = evidence
