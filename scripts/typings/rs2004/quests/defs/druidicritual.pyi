from typing import Sequence, Optional
from __builtins__ import Tile
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot

DRUIDIC_RITUAL_STAGE: Record
druidicritual: QuestModule

def parse_druidic_ritual_journal(lines: str | Sequence[str]) -> Optional[int]: ...
def druidic_ritual_area(tile: Optional[Tile]) -> str: ...
def decide(snap: QuestSnapshot) -> Record: ...
