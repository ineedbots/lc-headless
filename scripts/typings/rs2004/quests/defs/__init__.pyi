# rs2004.quests.defs: the quests, in the order the queue runs them. A quest is rs2004.quests.defs.<file>, exporting a
# QuestModule of the same name. See docs/scripting/quests.md.

from typing import Callable, Optional

from rs2004.quests.engine.types import QuestModule
from rs2004.quests.types import QuestRecord

ORDER: list[str]

class QuestDef:
    file: str
    record: QuestRecord
    def __init__(self, file: str, id: str, load: Callable[[], QuestModule]) -> None: ...
    def module(self) -> QuestModule: ...

QUEST_DEFS: list[QuestDef]

def def_by_id(id: str) -> Optional[QuestModule]: ...
def record_by_id(id: str) -> Optional[QuestRecord]: ...
