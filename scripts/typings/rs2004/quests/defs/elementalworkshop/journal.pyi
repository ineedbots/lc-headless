from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

ELEMENTAL_WORKSHOP_QUEST: str
EW_STAGE: Record
EW_FLAG: Record
def parse_elemental_workshop_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_elemental_workshop_progress() -> Wait[Any]: ...
