# rs2004.quests.engine.watchdog: the no-progress watchdog.

from rs2004.quests.engine.types import QuestSnapshot

NO_PROGRESS_WARN: int
NO_PROGRESS_PARK: int

def progress_signature(snap: QuestSnapshot) -> str: ...

class ProgressWatchdog:
    last: str
    count: int
    def note(self, signature: str) -> int: ...
    def note_failure(self, before: str, after: str) -> int: ...
    def reset(self) -> None: ...
