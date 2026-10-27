# quests/defs/princeali/journal.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


PRINCE_STAGE: Any
def parse_prince_journal(lines: Any) -> Any: ...
def read_prince_progress() -> Wait[Any]: ...
