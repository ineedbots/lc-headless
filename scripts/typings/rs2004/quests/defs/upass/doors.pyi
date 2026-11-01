from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def door_across(at: Any) -> Any: ...
def door_stands(at: Any) -> Any: ...
MUD_CAGE: Tile
MUD_CELL: Tile
def mud_cell_door(at: Any) -> Any: ...
