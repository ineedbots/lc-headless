from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def parse_chompy_journal(lines: Any) -> Optional[QuestProgress]: ...
def read_chompy_progress() -> Wait[Any]: ...
