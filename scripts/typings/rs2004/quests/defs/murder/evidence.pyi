from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def take_thread(log: Callable[[str], None]) -> Any: ...
def take_prints(order: Any, log: Callable[[str], None]) -> Wait[Any]: ...
