from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

FORM_ELEMENT: Any
RANGED_FORM: int
MELEE_FORM: int
IMMUNE_FORMS: Any
MOTHER_IDS: Any
def spell_tier(magic: Any) -> Any: ...
def fight_junior(log: Callable[[str], None]) -> Wait[Any]: ...
def fight_mother(log: Callable[[str], None]) -> Wait[Any]: ...
