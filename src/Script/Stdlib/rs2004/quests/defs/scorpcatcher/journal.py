"""Ported from rs2b0t's src/bot/api/ai/quests/defs/scorpcatcher/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.scorpcatcher.areas import SC_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests
import _core
from rs2004.quests.engine.types import QuestProgress

__all__ = ['QUEST', 'parse_scorpion_journal', 'read_scorpion_progress']

QUEST = 'Scorpion Catcher'


# Why: the journal only counts cages in the pack, so which scorpions are caught is read from the cage obj id, which works for a banked cage too.
def parse_scorpion_journal(lines):
    """`%scorpcatcher` from the journal page."""
    text = normalize(lines)

    def at(stage):
        return (QuestProgress(stage, set()))

    if ('quest complete!' in text):
        return at(SC_STAGE.COMPLETE)
    # Why: Hint blocks accumulate, so test stage markers newest-first.
    if ('the second kharid scorpion' in text):
        return at(SC_STAGE.SECOND_HINT)
    if ('the first kharid scorpion' in text):
        return at(SC_STAGE.FIRST_HINT)
    if ("i've spoken to thormac in the sorcerer's tower" in text):
        return at(SC_STAGE.STARTED)
    if ('i can start this quest by speaking to' in text) and ('thormac' in text):
        return at(SC_STAGE.NOT_STARTED)
    return None


def read_scorpion_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return QuestProgress(SC_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(SC_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    progress = parse_scorpion_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
