# rs2004.quests.armour: the armour a quest wears. A piece is a Record of id, name, slot, defence and ranged. See
# docs/scripting/quests.md.

from typing import Any, Optional

from rs2004.quests.engine.types import QuestSnapshot

TIERS: list[tuple[str, int]]
SHAPES: dict[str, list[str]]
QUEST_ARMOUR: list[Any]

def armour_worn(snap: QuestSnapshot, item: Any) -> bool: ...
def armour_held(snap: QuestSnapshot, item: Any) -> bool: ...
def armour_choice(snap: QuestSnapshot, slot: str) -> Optional[Any]: ...
