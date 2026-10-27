# quests/defs/doric.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


DORIC_STAGE: Any
DORIC_ITEM: Any
DORIC_PICKAXES: Any
def parse_doric_journal(lines: Any) -> Any: ...
def decide_for_mining_level(snap: QuestSnapshot, mining_level: Any, mining_xp: Any = 0) -> Record: ...
def decide(snap: QuestSnapshot) -> Record: ...
doric: QuestModule
