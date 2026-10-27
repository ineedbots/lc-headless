# quests/barcrawl/barcrawl_logic.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


COINS_ID: Any
BARCRAWL_CARD: Any
COINS: Any
BARS: Any
BARCRAWL_GP: Any
BARBARIAN_GUARD_ID: Any
GUARD_TILE: Any
GUARD_PREFER: Any
BAR_PREFER: Any
TOO_DRUNK: Any
GATE_IS_OPEN: Any
def parse_card(lines: Any) -> Any: ...
def next_bar(remaining: Any, here: Any) -> Any: ...
