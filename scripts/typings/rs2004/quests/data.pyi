# rs2004.quests.data: the 63 quest records. See docs/scripting/quests.md.

from typing import Optional

from rs2004.quests.types import QuestRecord

QUESTS: list[QuestRecord]

def quest_record(id: str) -> Optional[QuestRecord]: ...
