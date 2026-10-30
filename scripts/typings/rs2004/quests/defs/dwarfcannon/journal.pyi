from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

MC_STAGE: Record
MCANNON_QUEST: str
MC_FLAG: Record
def parse_dwarf_cannon_journal(lines: Any) -> Any: ...
def read_dwarf_cannon_progress() -> Wait[Any]: ...
