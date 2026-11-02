from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

LEGENDS_QUEST: Any
LQ_STAGE: Record
LQ_SKILLS: Record
LQ_ID: Record
LQ_ITEM: Record
LQ_NPC: Record
LQ_LOC: Record
LQ_LOC_ID: Record
LQ_BANK: Record
LQ_SHOP: Record
LQ_TILE: Record
GEM_ROCKS: Any
GEM_CUTS: Any
WALL_RUNES: Any
HEROES: Any
EVIL_TOTEMS: Any
FERTILE_SOILS: Any
JUNGLE_BAND: Record
def in_jungle_band(tile: Any) -> Any: ...
def legends_area(tile: Any) -> Any: ...
def in_octagram(tile: Any) -> Any: ...
def past_barrier(tile: Any) -> Any: ...
def on_viyeldi_ledge(tile: Any) -> Any: ...
def jungle_section(tile: Any) -> Any: ...
def on_open_ground(area: Any) -> Any: ...
