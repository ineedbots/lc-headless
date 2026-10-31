from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

TROLL_STAGE: Record
TROLL_QUEST: str
TROLL_FLAG: Record
def parse_troll_stronghold_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_troll_stronghold_progress() -> Wait[Any]: ...
