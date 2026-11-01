from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

from rs2004.quests.defs.tbwt.areas import TBWT_QUEST as TBWT_QUEST
from rs2004.quests.defs.tbwt.areas import TB_ID as TB_ID
from rs2004.quests.defs.tbwt.areas import TB_LUBUFU as TB_LUBUFU
from rs2004.quests.defs.tbwt.areas import TB_MAIN as TB_MAIN
from rs2004.quests.defs.tbwt.areas import TB_TAMAYU as TB_TAMAYU
from rs2004.quests.defs.tbwt.areas import TB_TIADECHE as TB_TIADECHE
from rs2004.quests.defs.tbwt.areas import TB_TINSAY as TB_TINSAY
from rs2004.quests.defs.tbwt.journal import parse_tbwt_journal as parse_tbwt_journal
from rs2004.quests.defs.tbwt.journal import read_tbwt_progress as read_tbwt_progress
from rs2004.quests.defs.tbwt.journal import TB_FLAG as TB_FLAG
from rs2004.quests.defs.tbwt.supplies import outstanding_supplies as outstanding_supplies
from rs2004.quests.defs.tbwt.supplies import prepare as prepare
from rs2004.quests.defs.tbwt.supplies import TB_PROVEN as TB_PROVEN
def decide(snap: QuestSnapshot) -> Record: ...
tbwt: QuestModule
