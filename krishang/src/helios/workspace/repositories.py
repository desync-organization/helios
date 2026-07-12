import hashlib
from pathlib import Path


def safe_join(root: Path, *parts: str) -> Path:
    root = root.resolve()
    candidate = root.joinpath(*parts).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path traversal rejected")
    return candidate


class RepositoryNamespace:
    def __init__(self, workspace_root: Path, repository: str, task_id: str) -> None:
        repo_key = hashlib.sha256(repository.encode()).hexdigest()[:16]
        self.root = safe_join(workspace_root, repo_key, task_id)
        self.repo = safe_join(self.root, "repo")
        self.artifacts = safe_join(self.root, "artifacts")
        self.logs = safe_join(self.root, "logs")

    def create(self) -> "RepositoryNamespace":
        for path in (self.repo, self.artifacts, self.logs):
            path.mkdir(parents=True, exist_ok=True)
        return self

