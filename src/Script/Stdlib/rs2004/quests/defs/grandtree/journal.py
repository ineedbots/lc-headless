"""Ported from rs2b0t's src/bot/api/ai/quests/defs/grandtree/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.game import reader
from rs2004.quests.defs.grandtree.areas import GT_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['QUEST', 'parse_grand_tree_journal', 'reset_grand_tree_stage', 'read_grand_tree_stage']

QUEST = 'The Grand Tree'
# Why: every finished stage stays on the page as a `@str@` line, several word-for-word the `@dbl@` line of the stage before, so needles match newest-first.
# Why: no needle spans a colour tag, because stripping one leaves a space where it stood.
NEEDLES = [
    [GT_STAGE.COMPLETE, 'quest complete!'],
    [GT_STAGE.SEARCHING_DACONIA, 'king narnode has seen the light'],
    [GT_STAGE.DEFEATED_BLACK_DEMON, 'he should be in these caves somewhere'],
    [GT_STAGE.UNLOCKED_TRAPDOOR, "i should investigate what's behind the"],
    [GT_STAGE.GIVEN_TWIGS, "isn't convinced but gave me some"],
    [GT_STAGE.FOUND_INVASION_PLANS, 'i should talk to the king and see what he says'],
    [GT_STAGE.CLUE_CHARLIE, 'has suggested i ask'],
    [GT_STAGE.OBTAINED_LUMBER_ORDER, 'i have an invoice that the foreman had'],
    [GT_STAGE.RELEASED_PRISON, 'has told me to use the'],
    [GT_STAGE.FOUND_JOURNAL, 'i should go speak to him again'],
    [GT_STAGE.SPOKEN_PRISONER, "and agreed to search glough's house"],
    [GT_STAGE.FOUND_PRISONER, 'said i can speak to'],
    [GT_STAGE.SPOKEN_GLOUGH, 'maybe i should have a chat with'],
    [GT_STAGE.RELAYED_MESSAGE, 'the king wants me to tell'],
    [GT_STAGE.SPOKEN_HAZELMERE, 'i then need to give the message'],
    [GT_STAGE.STARTED, 'he has asked me to take a'],
    [GT_STAGE.NOT_STARTED, 'i can start this quest at the'],
]


def parse_grand_tree_journal(lines):
    text = normalize(lines)
    for stage, needle in NEEDLES:
        if (needle in text):
            return stage
    return None


# Why: reading the journal opens a main modal, which the demon fight punishes, so the last reading is kept and only moves forward.
last_stage = None


def reset_grand_tree_stage():
    """Test hook; the cached floor survives between quests inside one bundle."""
    global last_stage
    last_stage = None


def read_grand_tree_stage():
    global last_stage
    status = quests.status(QUEST)
    if status == 'complete':
        last_stage = GT_STAGE.COMPLETE
        return last_stage
    if status == 'not_started':
        last_stage = GT_STAGE.NOT_STARTED
        return last_stage
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    parsed = parse_grand_tree_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if parsed is not None and (last_stage is None or parsed > last_stage):
        last_stage = parsed
    return (parsed if parsed is not None else last_stage)
