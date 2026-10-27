# quests/defs/princeali/__init__.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def decide(snap: QuestSnapshot) -> Record: ...
princeali: QuestModule
