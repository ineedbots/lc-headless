from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

PC_STAGE: Record
def parse_plague_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_plague_progress() -> Wait[Any]: ...
