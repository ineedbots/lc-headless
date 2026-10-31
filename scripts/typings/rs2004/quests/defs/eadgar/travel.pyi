from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def guarded(name: Any, run: Any) -> Any: ...
def guarded_talk(stop: Any) -> Any: ...
