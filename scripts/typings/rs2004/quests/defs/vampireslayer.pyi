# quests/defs/vampireslayer.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


VAMPIRE_SLAYER_STAGE: Any
def parse_vampire_slayer_journal(lines: Any) -> Any: ...
def vampire_slayer_area(tile: Any) -> Any: ...
def decide(snap: QuestSnapshot) -> Record: ...
vampireslayer: QuestModule
