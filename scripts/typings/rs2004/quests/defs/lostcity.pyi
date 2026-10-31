from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

LOST_CITY_STAGE: Record
def parse_lost_city_journal(lines: Any) -> Any: ...
LOST_CITY_FOOD_TARGET: Any
LOST_CITY_STAFF_TARGET: int
LOST_CITY_CAST_TARGET: Any
def lost_city_area(tile: Any) -> Any: ...
def decide(snap: QuestSnapshot) -> Record: ...
lostcity: QuestModule
