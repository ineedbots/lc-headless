from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

QUEST: str
def parse_scorpion_journal(lines: Any) -> Any: ...
def read_scorpion_progress() -> Wait[Any]: ...
