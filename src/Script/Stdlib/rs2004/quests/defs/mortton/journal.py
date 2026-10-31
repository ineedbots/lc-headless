"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.engine.types import QuestProgress

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.mortton.areas import SM_QUEST, SM_STAGE, SM_VARP
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['SM_FLAG', 'parse_mortton_journal', 'temple_flags', 'read_mortton_progress']

SM_FLAG = Record({'REPAIRED': 'repaired', 'RESOURCES': 'resources', 'SANCTITY': 'sanctity'})
# Why: mortton_journal.rs2 appends, so earlier prose is still on the page and the newest marker goes first.
MARKERS = [
    ['quest complete!', SM_STAGE.COMPLETE],
    ['the shades spirit was released', SM_STAGE.LIT_PYRE],
    ['i placed some pyre logs onto a funeral pyre', SM_STAGE.LOGS_ON_PYRE],
    ['i used sacred oil on logs turning them into pyre logs', SM_STAGE.CREATED_PYRE_LOGS],
    ['i placed a flask of olive oil in the flame', SM_STAGE.CREATED_SACRED_OIL],
    ['i helped rebuild the temple using limestone bricks', SM_STAGE.CAN_LIGHT_ALTAR],
    ["i've started rebuilding the temple", SM_STAGE.REBUILD_TEMPLE],
    ["he's quite interested in 'flaemtaer temple'", SM_STAGE.ULSQUIRE_TEMPLE],
    ['maybe if i investigate around here a little more', SM_STAGE.SHADES_TO_ULSQUIRE],
    ['i should show the shade remains to', SM_STAGE.SHADES_TO_RAZMIRE],
    ["i've killed all five shades", SM_STAGE.KILLED_5],
    ["i've killed four shades", SM_STAGE.KILLED_4],
    ["i've killed three shades", SM_STAGE.KILLED_3],
    ["i've killed two shades", SM_STAGE.KILLED_2],
    ["i've killed one shade", SM_STAGE.KILLED_1],
    ['i have to kill five shades', SM_STAGE.KILL_SHADES],
    ['i used the serum on a local npc', SM_STAGE.MADE_SERUM],
    ['i made serum 207 from tarromin', SM_STAGE.MADE_SERUM],
    ['and i found the town of', SM_STAGE.READ_DIARY],
    ['i can start this quest by exploring the town of', SM_STAGE.NOT_STARTED],
]


def parse_mortton_journal(lines):
    text = normalize(lines)
    hit = ([marker for marker in MARKERS if marker[0] in text] or [None])[0]
    return None if hit is None else hit[1]


# Why: the 3 flamtaer meters are `transmit=yes`, so the temple leg reads them without opening anything; Razmire's ai_timer only recomputes them in the temple zone, so they're stale elsewhere.
def temple_flags():
    """The three transmitted flamtaer meters, as counted flags."""
    return set([
        f'{SM_FLAG.REPAIRED}:{reader.varp(SM_VARP.TEMPLE_REPAIRED)}',
        f'{SM_FLAG.RESOURCES}:{reader.varp(SM_VARP.TEMPLE_RESOURCES)}',
        f'{SM_FLAG.SANCTITY}:{reader.varp(SM_VARP.TEMPLE_SANCTITY)}',
    ])


last_stage = None


def read_mortton_progress():
    global last_stage
    status = quests.status(SM_QUEST)
    if status == 'complete':
        return QuestProgress(SM_STAGE.COMPLETE, temple_flags())
    if status == 'not_started':
        return QuestProgress(SM_STAGE.NOT_STARTED, temple_flags())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(SM_QUEST)
    stage = parse_mortton_journal(_w2)
    # Why: a mesbox left on main blanks every journal read behind it, and the temple refuses in mesboxes.
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if stage is not None:
        last_stage = stage
    settled = (stage if stage is not None else last_stage)
    return (None if settled is None else QuestProgress(settled, temple_flags()))
