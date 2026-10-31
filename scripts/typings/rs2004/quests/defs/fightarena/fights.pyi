from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FA_FIGHT: Record
PROTECT_MELEE: str
PROTECT_LEVEL: int
def fight_won(swings: Any, missing_ticks: Any) -> Any: ...
def run_fight(fight: Any, log: Callable[[str], None]) -> Wait[Any]: ...
