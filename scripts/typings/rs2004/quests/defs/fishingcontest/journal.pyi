from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FC_STAGE: Record
def parse_fishing_contest_journal(lines: str | Sequence[str]) -> Optional[int]: ...
def read_fishing_contest_stage() -> Wait[Any]: ...
