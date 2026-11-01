from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def verdict_since(mark: Any) -> Any: ...
def said_since(mark: Any, count: Any, separator: Any = ' / ') -> Any: ...
