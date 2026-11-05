from typing import Any, Optional, Sequence
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestSnapshot


def ids(items) -> Any: ...
QUEST_IDS: Any
MATERIAL_FOOD: Any
EQUIPMENT_IDS: Any
PROTECTED_IDS: Any
FOODS: Any
def resume_preparation(module: QuestModule, snap: QuestSnapshot, inventory: Sequence[Any], food: Optional[str]) -> Optional[Record]: ...
