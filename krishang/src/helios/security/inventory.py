from pathlib import Path

from helios.contracts.security import RepositoryInventory


LANGUAGE_EXTENSIONS = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".rs": "Rust", ".go": "Go", ".java": "Java", ".cs": "C#",
}
MANIFEST_NAMES = {"package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml"}
LOCK_NAMES = {"bun.lock", "package-lock.json", "pnpm-lock.yaml", "uv.lock", "poetry.lock", "Cargo.lock", "go.sum"}


def inventory_repository(root: Path, repository: str, commit_sha: str, excluded: list[str] | None = None) -> RepositoryInventory:
    excluded = excluded or [".git", "node_modules", ".next"]
    languages: set[str] = set()
    manifests: list[str] = []
    lockfiles: list[str] = []
    workflows: list[str] = []
    infra: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts) or not path.is_file():
            continue
        if path.suffix in LANGUAGE_EXTENSIONS:
            languages.add(LANGUAGE_EXTENSIONS[path.suffix])
        if path.name in MANIFEST_NAMES:
            manifests.append(relative.as_posix())
        if path.name in LOCK_NAMES:
            lockfiles.append(relative.as_posix())
        if relative.as_posix().startswith(".github/workflows/"):
            workflows.append(relative.as_posix())
        if path.name in {"Dockerfile", "docker-compose.yml", "terraform.tf", "wrangler.toml"}:
            infra.append(relative.as_posix())
    limitations = [] if languages else ["No supported source-language files were found"]
    return RepositoryInventory(repository=repository, commit_sha=commit_sha, languages=sorted(languages),
                               manifests=sorted(manifests), lockfiles=sorted(lockfiles),
                               workflows=sorted(workflows), infrastructure_files=sorted(infra),
                               coverage_limitations=limitations)

