from typing import Optional, Sequence
from __builtins__ import Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FLUFFS_STAGE: Record
FLUFFS_OBJ: Record
gertrudescat: QuestModule

def parse_gertrudes_cat_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_gertrudes_cat_progress() -> Wait[Optional[QuestProgress]]: ...
def decide(snap: QuestSnapshot) -> Record: ...
