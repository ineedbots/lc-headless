from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

UP_STAGE: Record
UP_FLAG: Record
UPASS: str
def parse_upass_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_upass_progress() -> Wait[Any]: ...
