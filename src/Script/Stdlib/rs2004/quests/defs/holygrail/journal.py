"""Ported from rs2b0t's src/bot/api/ai/quests/defs/holygrail/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.holygrail.areas import GRAIL_NAME
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['GRAIL_STAGE', 'parse_holy_grail_journal', 'read_holy_grail_progress']

GRAIL_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 2,
    'SPOKEN_MERLIN': 3,
    'SPOKEN_CRONE': 4,
    'FAILED_TITAN': 7,
    'FINDING_PERCIVAL': 8,
    'GIVEN_WHISTLE': 9,
    'COMPLETE': 10,
})
# Why: every earlier line stays on the page struck through, so an early needle still matches late and only this order separates them.
STAGES = [
    ['quest complete!', GRAIL_STAGE.COMPLETE],
    ["i honoured the fisher king's request", GRAIL_STAGE.GIVEN_WHISTLE],
    ['the fisher king is very sick', GRAIL_STAGE.FINDING_PERCIVAL],
    ['i need to find a weapon', GRAIL_STAGE.FAILED_TITAN],
    ['i spoke to galahad in his shack', GRAIL_STAGE.SPOKEN_CRONE],
    ['according to a crone on entrana', GRAIL_STAGE.SPOKEN_CRONE],
    ['merlin suggested two things', GRAIL_STAGE.SPOKEN_MERLIN],
    ['i should start my quest by speaking to', GRAIL_STAGE.STARTED],
    ['i can start this quest by speaking to', GRAIL_STAGE.NOT_STARTED],
]


# Why: no flags; beating the titan never moves the varp or prints a line, so the crossing is read from where you stand and everything else is an item.
def parse_holy_grail_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    for needle, stage in STAGES:
        if needle in text:
            return QuestProgress(stage, set())
    return None


last_good = None


def read_holy_grail_progress():
    global last_good
    status = quests.status(GRAIL_NAME)
    if status == 'complete':
        return QuestProgress(GRAIL_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(GRAIL_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(GRAIL_NAME)
    progress = parse_holy_grail_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
