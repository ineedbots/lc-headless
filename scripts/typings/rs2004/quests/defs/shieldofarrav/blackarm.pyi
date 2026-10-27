# quests/defs/shieldofarrav/blackarm.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def raid_weapon_store(log: Callable[[str], None]) -> Wait[Any]: ...
def take_black_arm_half(log: Callable[[str], None]) -> Wait[Any]: ...
def blackarm_step(snap: QuestSnapshot) -> Any: ...
