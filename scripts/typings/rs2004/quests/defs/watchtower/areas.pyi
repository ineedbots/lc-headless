from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

WT_ITEM: Record
CRYSTALS: Any
RELIC_PARTS: Any
WT_LOC: Record
WT_NPC: Record
WT_TILE: Record
WT_CAVES: Any
WT_NIGHTSHADE: Record
def watchtower_area(tile: Any) -> Any: ...
