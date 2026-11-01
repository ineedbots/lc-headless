from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

DIG_NAME: str
DIG_ID: Record
DIG_ITEM: Record
DIG_NPC: Record
DIG_LOC: Record
DIG_SOIL_IDS: Any
DIG_ZONE: Record
DIG_TILE: Record
EXAMINER: Any
EXPERT: Any
CURATOR: Any
PANNING_GUIDE: Any
def in_shaft_east(t: Any) -> Any: ...
def in_shaft_west(t: Any) -> Any: ...
def in_altar_cave(t: Any) -> Any: ...
def in_dig_cave(t: Any) -> Any: ...
