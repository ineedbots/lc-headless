from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

from rs2004.quests.defs.trollstronghold.journal import parse_troll_stronghold_journal as parse_troll_stronghold_journal
from rs2004.quests.defs.trollstronghold.journal import read_troll_stronghold_progress as read_troll_stronghold_progress
from rs2004.quests.defs.trollstronghold.journal import TROLL_FLAG as TROLL_FLAG
from rs2004.quests.defs.trollstronghold.journal import TROLL_QUEST as TROLL_QUEST
from rs2004.quests.defs.trollstronghold.journal import TROLL_STAGE as TROLL_STAGE
from rs2004.quests.defs.trollstronghold.areas import troll_zone as troll_zone
from rs2004.quests.defs.trollstronghold.areas import committed as committed
from rs2004.quests.defs.trollstronghold.areas import ITEM as ITEM
from rs2004.quests.defs.trollstronghold.areas import COMBAT_FOODS as COMBAT_FOODS
from rs2004.quests.defs.trollstronghold.areas import FOOD_TARGET as FOOD_TARGET
from rs2004.quests.defs.trollstronghold.areas import FALADOR_WEST_BANK as FALADOR_WEST_BANK
def planned_gear(snap: QuestSnapshot) -> Any: ...
def wear_all(names: Any) -> Any: ...
def prepare(snap: QuestSnapshot, zone: Any = 'mainland') -> Any: ...
def steal_cell_key(guard: Any, key: Any, stand: Any, log: Callable[[str], None]) -> Wait[Any]: ...
def unlock_cell(key: Any, door: Any, stand: Any, log: Callable[[str], None]) -> Wait[Any]: ...
def decide(snap: QuestSnapshot) -> Record: ...
trollstronghold: QuestModule
