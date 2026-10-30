from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

SS_OBJ: Record
SS_ITEM: Record
SS_LOC: Record
SS_TILE: Record
KHAZARD_SHOP: Record
CAROLINE: Record
HOLGART_LAND: Record
HOLGART_PLATFORM: Record
HOLGART_ISLAND: Record
BAILEY: Record
KENT: Record
def on_platform(tile: Any) -> Any: ...
def on_island(tile: Any) -> Any: ...
