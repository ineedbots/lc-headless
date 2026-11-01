"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.game import reader
from rs2004.quests.defs.chompybird.areas import CB_QUEST, CB_STAGE
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['parse_chompy_journal', 'read_chompy_progress']

# Why: `chompybird_journal.rs2` appends earlier text, so test stage markers newest-first.
# Why: 15/20, 30/35 and 40/45 render identically; the step each pair wants is the same one, and the bow in the pack separates 40 from 45 where it matters.
MARKERS = [
    ['quest complete!', CB_STAGE.COMPLETE],
    ["i've cooked the chompy", CB_STAGE.CHOMPY_COOKED],
    ['i showed rantz the chompy', CB_STAGE.TOLD_TO_COOK],
    ["i've killed a chompy bird!", CB_STAGE.KILLED_CHOMPY],
    ['has lent me an ogre bow', CB_STAGE.GOT_BOW],
    ["doesn't seem to be a very good shot", CB_STAGE.RANTZ_MISSED],
    ['i dropped a fatsy toady on the spot', CB_STAGE.DROPPED_TOAD],
    ["i managed to trap some 'fatsy toadies'", CB_STAGE.SHOWN_TOAD],
    ["rantz told me 'fatsy toadies' grow fat on swamp gas", CB_STAGE.KIDS_PLAY_WITH_TOAD],
    ["it turned out that 'stabbers' are a kind of specially made", CB_STAGE.GIVEN_ARROWS],
    ["i agreed to get rants some 'stabbers'", CB_STAGE.STARTED],
    ['i can start this quest by speaking to the ogre', CB_STAGE.NOT_STARTED],
]


def parse_chompy_journal(lines):
    text = normalize(lines)
    for needle, stage in MARKERS:
        if needle in text:
            return QuestProgress(stage, set())
    return None


last_good = None


def read_chompy_progress():
    global last_good
    status = quests.status(CB_QUEST)
    if status == 'complete':
        return QuestProgress(CB_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(CB_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(CB_QUEST)
    progress = parse_chompy_journal(_w2)
    # Why: the ogre chest, the bait refusal and every objbox in Rantz's chain sit on main, and while one is up the journal read comes back empty.
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
