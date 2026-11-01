from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

IKOV_STAGE: Record
STAGES: list
def parse_ikov_journal(lines: Any) -> Any: ...
last_good: Any
def read_ikov_stage() -> Wait[Any]: ...
