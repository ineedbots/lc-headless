from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

WATCHTOWER_STAGE: Record
WATCHTOWER_QUEST: str
def parse_watchtower_journal(lines: Any) -> Optional[QuestProgress]: ...
def read_watchtower_progress() -> Wait[Any]: ...
