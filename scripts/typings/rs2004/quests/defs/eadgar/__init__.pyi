from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

from rs2004.quests.defs.eadgar.journal import EADGAR_FLAG as EADGAR_FLAG
from rs2004.quests.defs.eadgar.journal import EADGAR_QUEST as EADGAR_QUEST
from rs2004.quests.defs.eadgar.journal import EADGAR_STAGE as EADGAR_STAGE
from rs2004.quests.defs.eadgar.journal import parse_eadgar_journal as parse_eadgar_journal
from rs2004.quests.defs.eadgar.journal import read_eadgar_progress as read_eadgar_progress
from rs2004.quests.defs.eadgar.areas import eadgar_zone as eadgar_zone
from rs2004.quests.defs.eadgar.areas import committed as committed
def decide(snap: QuestSnapshot) -> Record: ...
eadgar: QuestModule
