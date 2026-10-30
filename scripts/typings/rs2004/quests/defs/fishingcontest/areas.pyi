from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FC_NAME: str
FC_ID: Record
FC_LOC: Record
RED_VINE_LOCS: Any
FC_NPC: Record
FC_TILE: Record
HARRY_SHOP: Record
DWARF_START: Record
DWARF_REPORT: Record
BONZO_ENTER: Record
BONZO_REPORT: Record
def in_compound(t: Any) -> Any: ...
def nearest_dwarf(t: Any) -> Any: ...
def nearest_spade(t: Any) -> Any: ...
