from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def usable_bows(ranged: Any) -> Any: ...
def bow_carried(snap: QuestSnapshot) -> Any: ...
ARDOUGNE_STORE: Record
TAVERLEY_HERBLORE: Record
CATHERBY_ARCHERY: Record
COAL_ROCKS: Tile
ARDOUGNE_RANGE: Tile
FOOD_TARGET: Any
WOOL_TARGET: int
ROPE_TARGET: int
ARROW_TARGET: int
STILL_FOOD: int
COAL_TARGET: int
BARREL_TARGET: int
def scan_bank() -> Any: ...
def withdraw(items: Any) -> Any: ...
def from_bank(snap: QuestSnapshot, item: Any, qty: Any) -> Any: ...
KIT: Any
KEEP_IDS: Any
RETURN_KIT: Any
def source_kit(snap: QuestSnapshot, kit: Any = None) -> Any: ...
def kit_shortfall(snap: QuestSnapshot, kit: Any = None) -> Any: ...
def source_coal(snap: QuestSnapshot) -> Any: ...
