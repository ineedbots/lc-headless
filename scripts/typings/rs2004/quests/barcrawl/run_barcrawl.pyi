# quests/barcrawl/run_barcrawl.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


def read_card(log: Callable[[str], None] = None) -> Wait[Any]: ...
def ensure_barcrawl(log: Callable[[str], None], on_progress: Any = None) -> Wait[Any]: ...
