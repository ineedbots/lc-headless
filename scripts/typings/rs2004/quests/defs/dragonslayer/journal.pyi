# quests/defs/dragonslayer/journal.py: rs2b0t quest parity.
from typing import Any, Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestProgress


DRAGON_STAGE: Any
def parse_dragon_journal(lines: Any) -> Any: ...
journal_read: Any
def describe_journal() -> Any: ...
def read_dragon_progress() -> Wait[Any]: ...
