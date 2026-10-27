# quests/defs/princeali/jailbreak.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def source_beers(snap: QuestSnapshot) -> Any: ...
def source_ropes(snap: QuestSnapshot) -> Any: ...
def decide_jailbreak(snap: QuestSnapshot) -> Any: ...
