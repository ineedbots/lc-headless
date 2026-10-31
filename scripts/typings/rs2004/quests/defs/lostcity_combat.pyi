from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

TREE_SPIRIT_SAFESPOT: Tile
TREE_SPIRIT_TRAP: Tile
TREE_STAND: Tile
LURE: Sequence[Any]
def highest_lost_city_strike(magic: Any, count: Any) -> Any: ...
def defeat_tree_spirit(log: Callable[[str], None], complete: Any) -> Wait[Any]: ...
