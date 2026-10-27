# quests/defs/shieldofarrav/partner.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


arrav_handoff_state: Any
def decide_handoff(state: Any) -> Any: ...
def run_handoff(handoff: Any, gang: Any, log: Callable[[str], None]) -> Wait[Any]: ...
def handoff_step(handoff: Any, gang: Any) -> Any: ...
