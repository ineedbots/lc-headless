from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FT_STAGE: Record
TRIALS: list
MERCHANT_STEPS: list
VOTES: list
def parse_fremennik_journal(lines: Any) -> Any: ...
last_good: Any
def reset_fremennik_journal_cache() -> Any: ...
def read_fremennik_progress() -> Wait[Any]: ...
