# rs2004.quests.exec.wool: balls of wool from the sheep up. See docs/scripting/quests.md.

from typing import Any, Callable

from __builtins__ import Tile, Wait
from rs2004.quests.engine.types import QuestSnapshot

UNSHEARED_SHEEP_ID: int

class WoolSites:
    pen: Tile
    wheel_stand: Tile
    shears_spawn: Tile
    spin_label: str
    def __init__(self, pen: Tile, wheel_stand: Tile, shears_spawn: Tile, spin_label: str) -> None: ...

def shear_one(pen: Tile, log: Callable[[str], None]) -> Wait[bool]: ...
def spin_all_wool(wheel_stand: Tile, log: Callable[[str], None]) -> Wait[bool]: ...
def gather_wool(snap: QuestSnapshot, need: int, sites: WoolSites) -> Any: ...
