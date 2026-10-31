from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

QUEST: str
SH_STAGE: Record
def parse_sheep_herder_journal(lines: Any) -> Any: ...
def read_sheep_herder_progress() -> Wait[Any]: ...
