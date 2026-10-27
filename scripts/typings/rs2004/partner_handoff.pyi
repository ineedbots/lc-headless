# partner_handoff.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


OPEN_REQUEST_EVERY_MS: Any
def decide_open_trade(state: Any) -> Any: ...
def run_handoff(spec: Any) -> Wait[Any]: ...
