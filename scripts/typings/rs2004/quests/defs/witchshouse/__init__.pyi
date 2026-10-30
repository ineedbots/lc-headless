from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def decide(snap: QuestSnapshot) -> Record: ...
witchshouse: QuestModule
from rs2004.quests.defs.witchshouse.journal import WH_STAGE as WH_STAGE
from rs2004.quests.defs.witchshouse.journal import parse_witchs_house_journal as parse_witchs_house_journal
from rs2004.quests.defs.witchshouse.journal import read_witchs_house_progress as read_witchs_house_progress
from rs2004.quests.defs.witchshouse.areas import WH_OBJ as WH_OBJ
from rs2004.quests.defs.witchshouse.areas import WH_TILE as WH_TILE
from rs2004.quests.defs.witchshouse.areas import in_garden as in_garden
from rs2004.quests.defs.witchshouse.areas import in_shed as in_shed
from rs2004.quests.defs.witchshouse.house import diary_state as diary_state
from rs2004.quests.defs.witchshouse.house import reset_diary_state as reset_diary_state
