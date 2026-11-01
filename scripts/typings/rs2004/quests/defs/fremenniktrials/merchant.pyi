from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

ASKELADDEN_FEE: int
HANDOVER: list
ASK: Record
def merchant_at(progress: Any) -> Any: ...
def merchant_step(snap: QuestSnapshot) -> Any: ...
def open_chain(log: Callable[[str], None]) -> Wait[Any]: ...
