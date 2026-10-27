# quests/defs/knightssword/__init__.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def decide_at(snap: QuestSnapshot, mining_level: Any, smithing_level: Any) -> Record: ...
def decide(snap: QuestSnapshot) -> Record: ...
knightssword: QuestModule
