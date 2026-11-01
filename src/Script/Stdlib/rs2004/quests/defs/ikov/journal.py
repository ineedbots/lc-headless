"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.ikov.areas import IKOV_QUEST
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['IKOV_STAGE', 'parse_ikov_journal', 'read_ikov_stage']

IKOV_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 10,
    'PULLED_LEVER': 30,
    'KILLED_WARRIOR': 40,
    'SPOKEN_WINELDA': 50,
    'PAID_WINELDA': 60,
    'HELPING_ARMADYL': 70,
    'COMPLETE': 100,
})
# Why: earlier lines stay on the page struck through, so an early needle still matches late and the order is what separates them.
STAGES = [
    ['quest complete!', IKOV_STAGE.COMPLETE],
    ['guardians of armadyl', IKOV_STAGE.HELPING_ARMADYL],
    ['winelda teleported me across', IKOV_STAGE.PAID_WINELDA],
    ['will teleport me across', IKOV_STAGE.SPOKEN_WINELDA],
    ['i killed it using arrows made of ice', IKOV_STAGE.KILLED_WARRIOR],
    ['i found a trap on a', IKOV_STAGE.PULLED_LEVER],
    ['he has given me a pendant so i can enter the', IKOV_STAGE.STARTED],
    ['i can start this quest at the', IKOV_STAGE.NOT_STARTED],
]


def parse_ikov_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    _v2 = ([(needle, _2) for needle, _2 in STAGES if (needle in text)] or [None])[0]
    return (_v2[1] if _v2 is not None else None)


last_good = None


def read_ikov_stage():
    global last_good
    status = quests.status(IKOV_QUEST)
    if status == 'complete':
        return IKOV_STAGE.COMPLETE
    if status == 'not_started':
        return IKOV_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    _w3 = yield from quests.journal(IKOV_QUEST)
    stage = parse_ikov_journal(_w3)
    # Why: the journal body is a main modal, and leaving it up makes every later read come back empty.
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if stage is not None:
        last_good = stage
    return (stage if stage is not None else last_good)
