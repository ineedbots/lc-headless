from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

GRAIL_NAME: str
ITEM: Record
MERLIN_ID: int
TITAN_ID: int
WHISTLE_DOOR_ID: int
GRAIL_TILE: Record
KING_ARTHUR_START: Any
KING_ARTHUR_FINISH: Any
MERLIN: Any
HIGH_PRIEST: Any
GALAHAD: Any
FISHERMAN: Any
FISHER_KING: Any
SIR_PERCIVAL: Any
LADY_OF_THE_LAKE: Any
def in_blighted_realm(t: Any) -> Any: ...
def in_renewed_realm(t: Any) -> Any: ...
def in_fisher_realm(t: Any) -> Any: ...
def east_of_titan(t: Any) -> Any: ...
def in_castle_upstairs(t: Any) -> Any: ...
