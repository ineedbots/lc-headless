from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def kill_the_warlord(log: Callable[[str], None]) -> Wait[Any]: ...
def clear_commander(log: Callable[[str], None]) -> Wait[Any]: ...
