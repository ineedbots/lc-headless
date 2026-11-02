from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def drink_prayer(log: Any) -> Wait[Any]: ...
def fight(plan: Any, log: Any) -> Wait[Any]: ...
