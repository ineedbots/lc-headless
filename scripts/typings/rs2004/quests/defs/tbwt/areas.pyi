from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

TBWT_QUEST: str
TB_VARP: Record
TB_MAIN: Record
TB_TIADECHE: Record
TB_TINSAY: Record
TB_TAMAYU: Record
TB_LUBUFU: Record
KARAMBWANJI_WANTED: int
KARAMBWAN_BAIT: int
TB_ID: Record
TB_NAME: Record
TB_SPEARS: Any
SPEAR_HUNT_KILLS: int
TB_SPEAR_IDS: Any
TB_SPEAR_DROPS: Any
AGILITY_DOSES: int
TB_POTIONS: Any
TB_POTION_IDS: Any
TB_BOWS: Any
TB_ARROWS: Any
TB_ARMOUR: Any
TB_ARMOUR_SLOTS: Any
ARROW_TARGET: int
FOOD_TARGET: Any
COIN_TARGET: int
TB_TILE: Record
TB_LOC: Record
TB_NPC: Record
TIMFRAKU_START: Record
TIMFRAKU_REWARD: Record
def on_karamja(t: Any) -> Any: ...
def in_cutscene(t: Any) -> Any: ...
