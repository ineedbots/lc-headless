from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

from rs2004.quests.defs.deathplateau.journal import DEATH_PLATEAU_QUEST as DEATH_PLATEAU_QUEST
from rs2004.quests.defs.deathplateau.journal import DP_FLAG as DP_FLAG
from rs2004.quests.defs.deathplateau.journal import DP_STAGE as DP_STAGE
from rs2004.quests.defs.deathplateau.journal import parse_death_plateau_journal as parse_death_plateau_journal
from rs2004.quests.defs.deathplateau.journal import read_death_plateau_progress as read_death_plateau_progress
from rs2004.quests.defs.deathplateau.journal import normalize_journal as normalize_journal
from rs2004.quests.defs.deathplateau.areas import ALL_BALL_IDS as ALL_BALL_IDS
from rs2004.quests.defs.deathplateau.areas import DEATH_ITEM as DEATH_ITEM
from rs2004.quests.defs.deathplateau.areas import FALADOR_WEST_BANK as FALADOR_WEST_BANK
from rs2004.quests.defs.deathplateau.areas import PEDESTALS as PEDESTALS
from rs2004.quests.defs.deathplateau.areas import TILE as TILE
from rs2004.quests.defs.deathplateau.harold import close_dice_if_open as close_dice_if_open
from rs2004.quests.defs.deathplateau.harold import inside_harold_room as inside_harold_room
def equip_floor(snap: QuestSnapshot, progress: Any) -> Any: ...
def effective_map(snap: QuestSnapshot, progress: Any) -> Any: ...
def decide(snap: QuestSnapshot) -> Record: ...
deathplateau: QuestModule
