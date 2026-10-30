from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

MURDER_STAGE: Record
POISON_PROVED: str
THREAD_FOUND: str
WEAPON_TAKEN: str
def parse_murder_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def read_murder_progress() -> Wait[Any]: ...
def reset_murder_progress_cache() -> Any: ...
