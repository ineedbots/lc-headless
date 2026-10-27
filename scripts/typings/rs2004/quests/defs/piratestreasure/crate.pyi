# quests/defs/piratestreasure/crate.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


CRATE_FULL: Any
def read_crate_messages(lines: Any) -> Any: ...
def search_banana_crate(log: Callable[[str], None]) -> Wait[Any]: ...
