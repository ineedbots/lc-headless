"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.quests.defs.shieldofarrav.areas import SOA_NAME
from rs2004.game import reader
from rs2004.tabs import quests

__all__ = ['SOA_STAGE', 'parse_shield_of_arrav_journal', 'read_shield_of_arrav_progress']

import _core
SOA_STAGE = Record({
    'NOT_STARTED': 0,
    'TOLD_OF_BOOK': 1,
    'READ_BOOK': 2,
    'SENT_TO_BARAEK': 3,
    'FIND_STRAVEN': 4,
    'KILL_JONNY': 8,
    'PHOENIX_JOINED': 9,
    'TRAMP_TOLD': 21,
    'KATRINE_TASK': 22,
    'BLACKARM_JOINED': 23,
    'COMPLETE': 30,
})
# Why: earlier lines stay on the page struck through, so an early needle still matches late and only this order separates them.
STAGES = [
    ['quest complete!', SOA_STAGE.COMPLETE],
    ['allowed me to join the black arm gang', SOA_STAGE.BLACKARM_JOINED],
    ['allowed me to join the phoenix gang', SOA_STAGE.PHOENIX_JOINED],
    ['stealing two phoenix crossbows', SOA_STAGE.KATRINE_TASK],
    ['in return for killing jonny the beard', SOA_STAGE.KILL_JONNY],
    ['he directed me to speak to katrine', SOA_STAGE.TRAMP_TOLD],
    ['about joining', SOA_STAGE.TRAMP_TOLD],
    ['i should find them and join', SOA_STAGE.FIND_STRAVEN],
    ['named baraek', SOA_STAGE.SENT_TO_BARAEK],
    ['if he knows anything more about this', SOA_STAGE.READ_BOOK],
    ['says there is a quest hidden in one of the books', SOA_STAGE.TOLD_OF_BOOK],
    ['i can start this quest by speaking to', SOA_STAGE.NOT_STARTED],
]
# Why: one stage renders several pages depending on what you carry, and the flag is what tells them apart.
FLAGS = [
    ['i should now give one to a fellow adventurer', 'two-certificates'],
    ['collect my reward', 'certificate'],
    ['i should take them both to the curator', 'both-halves'],
    ['can find the other shield half', 'own-half-only'],
    ['i should now return them to katrine', 'crossbows-held'],
    ['i should now be able to steal the crossbows', 'key-held'],
    ['i confronted and killed jonny the beard', 'report-held'],
]


def parse_shield_of_arrav_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    hit = ([needle for needle in STAGES if (needle[0] in text)] or [None])[0]
    if not hit:
        return None
    flags = set()
    for needle, flag in FLAGS:
        if (needle in text):
            flags.add(flag)
    # Why: the killed-Jonny line stays struck through after the hand-in, so it only counts while KILL_JONNY is the stage.
    if hit[1] != SOA_STAGE.KILL_JONNY:
        flags.discard('report-held')
    return Record({'stage': hit[1], 'flags': flags})


last_good = None


def read_shield_of_arrav_progress():
    global last_good
    status = quests.status(SOA_NAME)
    if status == 'complete':
        return Record({'stage': SOA_STAGE.COMPLETE, 'flags': set()})
    if status == 'not_started':
        return Record({'stage': SOA_STAGE.NOT_STARTED, 'flags': set()})
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(SOA_NAME)
    progress = parse_shield_of_arrav_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
