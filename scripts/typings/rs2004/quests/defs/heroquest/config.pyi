from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

hero_config: Record
cached: Any
cached_for: str
def hero_gang() -> Any: ...
def reset_hero_gang_cache() -> Any: ...
def partner_configured() -> Any: ...
