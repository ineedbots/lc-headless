from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def take_wampum_belt(log: Any) -> Wait[Any]: ...
def start_quest(log: Any) -> Wait[Any]: ...
