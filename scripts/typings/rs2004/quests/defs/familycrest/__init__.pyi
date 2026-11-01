from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def decide(snap: QuestSnapshot) -> Record: ...
familycrest: QuestModule
from rs2004.quests.defs.familycrest.journal import parse_family_crest_journal as parse_family_crest_journal
from rs2004.quests.defs.familycrest.journal import read_family_crest_progress as read_family_crest_progress
from rs2004.quests.defs.familycrest.journal import describe_journal as describe_journal
from rs2004.quests.defs.familycrest.areas import FC_STAGE as FC_STAGE
from rs2004.quests.defs.familycrest.areas import FC_ID as FC_ID
from rs2004.quests.defs.familycrest.areas import FC_ITEM as FC_ITEM
from rs2004.quests.defs.familycrest.areas import FC_NPC as FC_NPC
from rs2004.quests.defs.familycrest.areas import FC_QUEST as FC_QUEST
from rs2004.quests.defs.familycrest.areas import in_perfect_gold_zone as in_perfect_gold_zone
from rs2004.quests.defs.familycrest.mine import mine_region as mine_region
from rs2004.quests.defs.familycrest.chronozon import BLASTS as BLASTS
from rs2004.quests.defs.familycrest.chronozon import SAFESPOT as SAFESPOT
from rs2004.quests.defs.familycrest.supplies import CREST_KEEP_IDS as CREST_KEEP_IDS
from rs2004.quests.defs.familycrest.supplies import warn_family_crest_readiness as warn_family_crest_readiness
from rs2004.quests.defs.familycrest.supplies import FC_OFFICIAL_SKILLS as FC_OFFICIAL_SKILLS
from rs2004.quests.defs.familycrest.supplies import teleport_kit_top_up as teleport_kit_top_up
from rs2004.quests.defs.familycrest.supplies import teleport_kit_plan as teleport_kit_plan
from rs2004.quests.defs.familycrest.supplies import TELEPORT_KIT as TELEPORT_KIT
