from pathlib import Path

from helios.contracts import Artifact


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, artifact: Artifact) -> Path:
        target = self.root / f"{artifact.artifact_id}.json"
        if target.exists():
            existing = Artifact.model_validate_json(target.read_text(encoding="utf-8"))
            if existing.content_hash != artifact.content_hash:
                raise ValueError("artifact ID collision")
            return target
        target.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        return target

    def get(self, artifact_id: str) -> Artifact:
        if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in artifact_id):
            raise ValueError("invalid artifact ID")
        return Artifact.model_validate_json((self.root / f"{artifact_id}.json").read_text(encoding="utf-8"))
