from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

KIT_KEEP: Any
def kit_wanted(snap: QuestSnapshot) -> Any: ...
def decide(snap: QuestSnapshot) -> Record: ...
fightarena: QuestModule
