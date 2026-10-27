# quests/defs/ernest/basement.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


REGION_BOX: Any
def in_alcove(tile: Any) -> Any: ...
def basement_region(tile: Any) -> Any: ...
DOOR_OPEN: Any
CHAIN: Any
def leave_manor_basement(log: Callable[[str], None]) -> Wait[Any]: ...
def fetch_oil_can(log: Callable[[str], None]) -> Wait[Any]: ...
