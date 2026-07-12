from dataclasses import dataclass


@dataclass(slots=True)
class RevisionState:
    count: int = 0
    last_notes: tuple[str, ...] = ()

    def permit(self, notes: list[str]) -> bool:
        normalized = tuple(sorted(note.strip().lower() for note in notes))
        if self.count >= 1:
            return False
        self.count += 1
        self.last_notes = normalized
        return True

