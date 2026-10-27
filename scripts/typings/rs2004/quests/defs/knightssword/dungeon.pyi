# quests/defs/knightssword/dungeon.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def mine_blurite(log: Callable[[str], None]) -> Wait[Any]: ...
