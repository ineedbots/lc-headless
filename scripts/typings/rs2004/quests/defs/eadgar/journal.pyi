from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

EADGAR_STAGE: Record
EADGAR_QUEST: str
EADGAR_FLAG: Record
SCARECROW_NEED: Record
def parse_eadgar_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def mark_eadgar_freed() -> Any: ...
def read_eadgar_progress() -> Wait[Any]: ...
