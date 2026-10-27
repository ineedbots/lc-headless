# quests/defs/dragonslayer/supplies.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


SUPPLY: Any
SUPPLY_TOOLS: Any
def ensure_coins(need: Any, log: Callable[[str], None]) -> Wait[Any]: ...
def smith_nails(need: Any, log: Callable[[str], None]) -> Wait[Any]: ...
def in_plank_graveyard(t: Any) -> Any: ...
SUPPLY_GATHERS: Any
