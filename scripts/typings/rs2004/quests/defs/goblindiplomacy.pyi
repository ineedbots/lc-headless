# quests/defs/goblindiplomacy.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


GOBLIN_DIPLOMACY_COIN_TARGET: Any
GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE: Any
def goblin_mail_gather_step(snap: QuestSnapshot, need: Any = 1) -> Any: ...
def decide(snap: QuestSnapshot) -> Record: ...
goblindiplomacy: QuestModule
