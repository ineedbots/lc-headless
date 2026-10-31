from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

SC_STAGE: Record
CAGE_ID: Record
CAGE_NAME: str
SCORPION_NPC: dict
SC_ID: Record
SC_ITEM: Record
ANTIPOISON_DOSES: Sequence[Any]
ANTIPOISON_SHOP: Record
ANTIPOISON_GP: int
EVERY_CAGE: Any
EVERY_SCORPION: Sequence[Any]
SCORPION_LABEL: dict
def caught_in(cage_id: Any) -> Any: ...
def cage_with(caught: Any) -> Any: ...
SC_TILE: Record
THORMAC: Any
SEER: Any
ABBOT: Any
VELRAK: Any
JAILER_NPC: str
