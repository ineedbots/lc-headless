from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FC_QUEST: str
FC_STAGE: Record
FC_ID: Record
FC_ITEM: Record
DUEL_RING_IDS: Any
ANTIPOISON_IDS: Any
PICKAXES: Any
FC_NPC: Record
FC_SHOP: Record
FC_LOC: Record
FC_BANK: Record
def in_perfect_gold_zone(tile: Any) -> Any: ...
def in_chronozon_lair(tile: Any) -> Any: ...
