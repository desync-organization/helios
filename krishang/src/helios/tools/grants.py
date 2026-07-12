from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolGrantPolicy:
    allowed: frozenset[str]

    def require(self, requested: list[str]) -> None:
        denied = set(requested) - self.allowed
        if denied:
            raise PermissionError(f"tool grants denied: {sorted(denied)}")

