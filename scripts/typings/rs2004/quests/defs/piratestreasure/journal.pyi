# quests/defs/piratestreasure/journal.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def parse_pirates_treasure_journal(lines: Any) -> Any: ...
def read_pirates_treasure_progress() -> Wait[Any]: ...
