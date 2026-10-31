from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

SHEEP: Sequence[Any]
ORDINAL: dict
BONES_OBJ: dict
PROD_OBJ: int
FEED_OBJ: int
JACKET_OBJ: int
TROUSERS_OBJ: int
FURNACE_LOC: int
GATE_LOC: Sequence[Any]
PROD: str
FEED: str
JACKET: str
TROUSERS: str
def sheep_name(n: Any) -> Any: ...
HALGRIVE: Any
ORBON: Any
SHEEP_SPAWN: dict
BANK: Tile
GATE_OUTSIDE: Tile
GATE_INSIDE: Tile
FURNACE_STAND: Tile
PROD_SPAWN: Tile
PEN: Record
GATE_ZONE: Record
def in_box(box: Any, t: Any) -> Any: ...
