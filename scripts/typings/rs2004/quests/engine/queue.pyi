# rs2004.quests.engine.queue: which quest runs next, and the queue's rows.

from typing import Mapping, Optional, Sequence

from rs2004.quests.types import QuestEligibility

class QueueRow:
    id: str
    name: str
    status: str
    reasons: list[str]
    def __init__(self, id: str = '', name: str = '', status: str = 'UNKNOWN', reasons: Optional[list[str]] = None) -> None: ...

def next_quest(order: Sequence[str], picked: set[str], elig: Mapping[str, QuestEligibility], parked: set[str]) -> Optional[str]: ...
def queue_rows(order: Sequence[str], picked: set[str], elig: Mapping[str, QuestEligibility], parked: set[str], running_id: Optional[str]) -> list[QueueRow]: ...
