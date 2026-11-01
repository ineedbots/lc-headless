from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def decide(snap: QuestSnapshot) -> Record: ...
elementalworkshop: QuestModule
from rs2004.quests.defs.elementalworkshop.journal import parse_elemental_workshop_journal as parse_elemental_workshop_journal
from rs2004.quests.defs.elementalworkshop.journal import EW_STAGE as EW_STAGE
from rs2004.quests.defs.elementalworkshop.journal import EW_FLAG as EW_FLAG
from rs2004.quests.defs.elementalworkshop.journal import ELEMENTAL_WORKSHOP_QUEST as ELEMENTAL_WORKSHOP_QUEST
from rs2004.quests.defs.elementalworkshop.areas import ew_area as ew_area
from rs2004.quests.defs.elementalworkshop.areas import EW_ITEM as EW_ITEM
from rs2004.quests.defs.elementalworkshop.areas import SEERS_BANK as SEERS_BANK
from rs2004.quests.defs.elementalworkshop.supplies import held as held
from rs2004.quests.defs.elementalworkshop.supplies import has_pickaxe as has_pickaxe
from rs2004.quests.defs.elementalworkshop.supplies import has_held_slash_tool as has_held_slash_tool
from rs2004.quests.defs.elementalworkshop.supplies import has_slash_tool as has_slash_tool
from rs2004.quests.defs.elementalworkshop.supplies import has_weapon as has_weapon
from rs2004.quests.defs.elementalworkshop.supplies import COAL_NEED as COAL_NEED
from rs2004.quests.defs.elementalworkshop.supplies import FOOD_WITHDRAW as FOOD_WITHDRAW
from rs2004.quests.defs.elementalworkshop.supplies import EW_OFFICIAL_SKILLS as EW_OFFICIAL_SKILLS
from rs2004.quests.defs.elementalworkshop.supplies import EW_PROVEN_COMBAT_FLOOR as EW_PROVEN_COMBAT_FLOOR
from rs2004.quests.defs.elementalworkshop.supplies import EW_FAILED_COMBAT as EW_FAILED_COMBAT
from rs2004.quests.defs.elementalworkshop.supplies import EW_PROBE_COMBAT as EW_PROBE_COMBAT
from rs2004.quests.defs.elementalworkshop.supplies import EW_TESTED_COMBAT as EW_TESTED_COMBAT
from rs2004.quests.defs.elementalworkshop.supplies import EW_RECOMMENDED_COMBAT as EW_RECOMMENDED_COMBAT
from rs2004.quests.defs.elementalworkshop.supplies import warn_elemental_workshop_readiness as warn_elemental_workshop_readiness
from rs2004.quests.defs.elementalworkshop.supplies import surface_loadout as surface_loadout
