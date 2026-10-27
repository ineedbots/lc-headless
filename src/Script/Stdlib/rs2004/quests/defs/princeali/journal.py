"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.interfaces import interfaces
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests


__all__ = ['PRINCE_STAGE', 'parse_prince_journal', 'read_prince_progress']

PRINCE_QUEST = 'Prince Ali Rescue'
PRINCE_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 10,
    'SPOKEN_OSMAN': 20,
    'PREP_FINISHED': 30,
    'GUARD_DRUNK': 40,
    'TIED_KELI': 50,
    'SAVED': 100,
    'COMPLETE': 110,
})
# Newest first: every entry keeps the earlier history.
STAGE_LINES = [
    ['quest complete!', PRINCE_STAGE.COMPLETE],
    ['i then used a wig, a skirt and some skin paste', PRINCE_STAGE.SAVED],
    ['i used my rope to tie up lady', PRINCE_STAGE.TIED_KELI],
    ['i also had to prevent the guard from seeing what i was up', PRINCE_STAGE.GUARD_DRUNK],
    ['i need to deal with the', PRINCE_STAGE.PREP_FINISHED],
    ['for advice', PRINCE_STAGE.SPOKEN_OSMAN],
    ['i should go and speak to', PRINCE_STAGE.STARTED],
    ['i can start this quest by speaking to', PRINCE_STAGE.NOT_STARTED],
]


def parse_prince_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    for needle, stage in STAGE_LINES:
        if (needle in text):
            return Record({'stage': stage, 'flags': set()})
    return None


def read_prince_progress():
    status = quests.status(PRINCE_QUEST)
    if status == 'complete':
        return Record({'stage': PRINCE_STAGE.COMPLETE, 'flags': set()})
    if status == 'not_started':
        return Record({'stage': PRINCE_STAGE.NOT_STARTED, 'flags': set()})
    if status != 'in_progress':
        return None
    # Why: the journal won't open while another box is up, since Quests.journal waits for modals().main to change and the quest-list button is dropped during a chat dialogue.
    # Why: Several steps end on a mesbox, so an empty read means unavailable rather than a stage reset.
    for attempt in range(3):
        yield from close_main_modal()
        _w1 = yield from quests.journal(PRINCE_QUEST)
        progress = parse_prince_journal(_w1)
        yield from close_main_modal()
        if progress:
            return progress
        yield from execution.delay_ticks(1)
    return None


def close_main_modal():
    if reader.modals().main == -1:
        return
    _core.close_interfaces()
    yield from execution.delay_until(lambda: reader.modals().main == -1, 2000)
