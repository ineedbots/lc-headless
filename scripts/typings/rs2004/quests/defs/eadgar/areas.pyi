from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

ER_ITEM: Record
LIQUORS: Any
ER_LOC: Record
ER_NPC: Record
CHICKEN_NPC_ID: int
ER_TILE: Record
THISTLE_SPOTS: Any
SANFEW_START: Record
SANFEW_FINISH: Record
EADGAR_TALK: Record
BURNTMEAT_TALK: Record
TEGID_ROBE: Record
PETE_WHEN: Record
PETE_FEED: Record
def eadgar_zone(tile: Any) -> Any: ...
def committed(zone: Any) -> Any: ...
def quest_bank(snap: QuestSnapshot) -> Any: ...
def held(snap: QuestSnapshot, item: Any) -> Any: ...
def banked(snap: QuestSnapshot, item: Any) -> Any: ...
def owned(snap: QuestSnapshot, item: Any) -> Any: ...
def worn(snap: QuestSnapshot, item: Any) -> Any: ...
