from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

OUT_OF_CAGES: Any
TO_RAILINGS: Any
def outstanding_crossing(chain: Any = None) -> Any: ...
def take_next_crossing(log: Callable[[str], None], chain: Any = None) -> Wait[Any]: ...
def reach_loose_railings(log: Callable[[str], None]) -> Wait[Any]: ...
