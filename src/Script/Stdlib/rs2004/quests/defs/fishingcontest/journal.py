"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fishingcontest/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.tabs import quests
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.quests.defs.fishingcontest.areas import FC_NAME
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record
import _core

__all__ = ['FC_STAGE', 'parse_fishing_contest_journal', 'read_fishing_contest_stage']

FC_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'IN_COMP': 2, 'GARLIC_COMP': 3, 'WON_COMP': 4, 'COMPLETE': 5})
# Why: the page is rebuilt from scratch at each stage but its first 2 lines are shared from `started` on, so these needles are the lines that differ.
STAGES = [
    ['quest complete!', FC_STAGE.COMPLETE],
    ['i easily won the contest', FC_STAGE.WON_COMP],
    ['next to the pipes', FC_STAGE.GARLIC_COMP],
    ['next to the willow tree', FC_STAGE.IN_COMP],
    ['fishing contest pass', FC_STAGE.STARTED],
    ['i can start this quest by speaking to', FC_STAGE.NOT_STARTED],
]


def parse_fishing_contest_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    hit = ([entry for entry in STAGES if entry[0] in text] or [None])[0]
    return hit[1] if hit is not None else None


# Why: Losing resets the stage to `started`, so a last-good cache could retain invalid progress.
def read_fishing_contest_stage():
    status = quests.status(FC_NAME)
    if status == 'complete':
        return FC_STAGE.COMPLETE
    if status == 'not_started':
        return FC_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(FC_NAME)
    stage = parse_fishing_contest_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage
