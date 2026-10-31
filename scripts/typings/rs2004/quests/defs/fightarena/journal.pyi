from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FIGHT_ARENA_QUEST: str
FA_STAGE: Record
def parse_fight_arena_journal(lines: Any) -> Any: ...
def reset_fight_arena_stage() -> Any: ...
def read_fight_arena_stage() -> Wait[Any]: ...
