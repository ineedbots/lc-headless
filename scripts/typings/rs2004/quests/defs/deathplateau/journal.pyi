from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

DEATH_PLATEAU_QUEST: str
DP_STAGE: Record
DP_FLAG: Record
def parse_death_plateau_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_death_plateau_progress() -> Wait[Any]: ...
