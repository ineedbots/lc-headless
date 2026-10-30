from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

TOTEM_STAGE: Record
LABEL_OBJ: int
TOTEM_OBJ: int
def in_mansion(tile: Any) -> Any: ...
COMBINATION: str
def parse_tribal_totem_journal(lines: str | Sequence[str]) -> Optional[QuestProgress]: ...
def decide(snap: QuestSnapshot) -> Record: ...
tribaltotem: QuestModule
