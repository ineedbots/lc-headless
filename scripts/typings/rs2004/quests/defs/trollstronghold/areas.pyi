from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

ITEM: Record
BOOT_COST: int
COIN_FLOAT: int
FOOD_TARGET: Any
FOOD_FLOOR: int
PRAYER_POTIONS: Sequence[Any]
PRAYER_POTION_TARGET: int
PRAYER_SIP_AT: float
COMBAT_FOODS: Sequence[Any]
FALADOR_WEST_BANK: Tile
TILE: Record
def troll_zone(tile: Any) -> Any: ...
def committed(zone: Any) -> Any: ...
DENULTH_START: Any
DUNSTAN_FINISH: Any
TENZING_BOOTS: Any
TENZING_DONE_RULES: Sequence[Any]
