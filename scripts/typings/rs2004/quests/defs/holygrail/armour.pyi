from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

ARMOUR_KEEP: Any
unwearable: Any
def reset_unwearable() -> Any: ...
def armour_wanted(snap: QuestSnapshot) -> Any: ...
