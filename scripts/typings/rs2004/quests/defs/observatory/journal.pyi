from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def parse_observatory_journal(lines: Any) -> Any: ...
def read_observatory_stage() -> Wait[Any]: ...
