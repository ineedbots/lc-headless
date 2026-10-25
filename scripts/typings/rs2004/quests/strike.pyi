# rs2004.quests.strike: Strike spells for the quests that fight with them. See docs/scripting/quests.md.

from typing import Any, Callable, Optional, Sequence

from rs2004.quests.engine.types import QuestSnapshot

STRIKE_CASTS: int
STRIKE_RUNES: list[str]
STRIKES: list[str]
BETTY: dict[str, Any]

def strike_spell(magic: int, count: Optional[Callable[[str], int]] = None) -> Optional[str]: ...
def prepare_strikes(snap: QuestSnapshot, keep: Optional[Sequence[str]] = None) -> Any: ...
