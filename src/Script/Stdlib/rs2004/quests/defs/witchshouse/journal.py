"""Ported from rs2b0t's src/bot/api/ai/quests/defs/witchshouse/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.tabs import quests
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.defs.witchshouse.areas import WITCHS_HOUSE_QUEST
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record
import _core

__all__ = ['WH_STAGE', 'parse_witchs_house_journal', 'read_witchs_house_progress']

WH_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'FOUND_MAGNET': 2,
    'UNLOCKED_DOOR': 3,
    'READ_DIARY': 5,
    'DEFEATED': 6,
    'COMPLETE': 7,
})


def normalize(lines):
    return ' ' + normalize_journal(lines)


# Why: the page keeps every earlier line struck through, so the magnet line is still on the back-door page and only this order separates them.
# Why: stages 3 and 5 render from one branch of `ball_journal.rs2`, so the diary read is invisible here and `DiaryState` carries it instead.
STAGES = [
    [' quest complete!', WH_STAGE.COMPLETE],
    [' now the shapeshifter is dead', WH_STAGE.DEFEATED],
    [' i have worked out how to unlock the back door', WH_STAGE.UNLOCKED_DOOR],
    [' i have found a magnet in a cupboard', WH_STAGE.FOUND_MAGNET],
    [' i should find a way into the garden', WH_STAGE.STARTED],
    [' i can start this quest', WH_STAGE.NOT_STARTED],
]


def parse_witchs_house_journal(lines):
    """Journal text to a varp-aligned stage."""
    text = normalize(lines)
    hit = ([entry for entry in STAGES if entry[0] in text] or [None])[0]
    return (QuestProgress(hit[1], set()) if hit else None)


# Why: `witch.rs2` can reset the varp from 3 to 1, so do not retain a later cached stage.
def read_witchs_house_progress():
    status = quests.status(WITCHS_HOUSE_QUEST)
    if status == 'complete':
        return QuestProgress(WH_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(WH_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(WITCHS_HOUSE_QUEST)
    progress = parse_witchs_house_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
