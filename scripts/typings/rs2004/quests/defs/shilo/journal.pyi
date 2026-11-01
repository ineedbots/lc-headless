from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

SHILO_QUEST: str
SV_STAGE: Record
def parse_shilo_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_shilo_progress() -> Wait[Any]: ...
