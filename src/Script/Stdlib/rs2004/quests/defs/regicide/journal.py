"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['RG_STAGE', 'RG_FLAG', 'REGICIDE', 'parse_regicide_journal', 'read_regicide_progress']

# Why: these are the `%regicide_quest` values themselves, so `--stage N` in the harness and the module's stage are one scale.
RG_STAGE = Record({
    'NOT_STARTED': 0,
    'RECEIVED_MESSAGE': 1,
    'SPOKEN_LATHAS': 2,
    'SPOKEN_SCOUTS': 3,
    'SPOKEN_IORWERTH': 4,
    'SPOKEN_TRACKER': 5,
    'SHOWN_PENDANT': 6,
    'FOUND_FOOTPRINTS': 7,
    'SPOKEN_TRACKER2': 8,
    'DEFEATED_GUARD': 9,
    'ENTERED_CAMP': 10,
    'SPOKEN_IORWERTH2': 11,
    'KILLED_TYRAS': 12,
    'REPORTED_IORWERTH': 13,
    'SPOKEN_ARIANWYN': 14,
    'COMPLETE': 15,
})
RG_FLAG = Record({'PENDANT': 'pendant', 'CHEMIST': 'chemist'})
REGICIDE = 'Regicide'
# Why: the journal is additive, every stage keeps the earlier lines and appends its own, so the deepest matching line wins and the list runs from the end of the quest backwards.
STAGE_LINES = [
    ['quest complete!', RG_STAGE.COMPLETE],
    ['when returning home i met an elf', RG_STAGE.SPOKEN_ARIANWYN],
    ['has given me a message to carry to', RG_STAGE.REPORTED_IORWERTH],
    ['the catapult provided a great way', RG_STAGE.KILLED_TYRAS],
    ['has given me a book', RG_STAGE.SPOKEN_IORWERTH2],
    ['i have found the camp of king tyras', RG_STAGE.ENTERED_CAMP],
    ['pushing my way through the undergrowth', RG_STAGE.DEFEATED_GUARD],
    ['i asked the tracker about the tracks', RG_STAGE.SPOKEN_TRACKER2],
    ['i have found some tracks leading off', RG_STAGE.FOUND_FOOTPRINTS],
    ['after proving that i was not a bandit', RG_STAGE.SHOWN_PENDANT],
    ['has given me his pendant as proof', RG_STAGE.SPOKEN_TRACKER],
    ["the tracker didn't trust me", RG_STAGE.SPOKEN_TRACKER],
    ['has offered the help of one of his', RG_STAGE.SPOKEN_IORWERTH],
    ['i have met a elvish scout party', RG_STAGE.SPOKEN_SCOUTS],
    ['asked me to re-enter the underground', RG_STAGE.SPOKEN_LATHAS],
    ['a courier has given me a message', RG_STAGE.RECEIVED_MESSAGE],
    ['will send word when i can start', RG_STAGE.NOT_STARTED],
    ['king lathas in ardougne castle', RG_STAGE.NOT_STARTED],
]
FLAG_LINES = [['has given me his pendant as proof', RG_FLAG.PENDANT], ['the chemist read the book', RG_FLAG.CHEMIST]]


def parse_regicide_journal(lines):
    """Stage plus sub-progress from the journal text. Why: `%regicide_quest` and `%regicide_bits` are both `scope=perm` with no `transmit`, so the journal scroll is the only client-visible record of either."""
    text = normalize(lines)
    hit = ([(needle, _2) for needle, _2 in STAGE_LINES if (needle in text)] or [None])[0]
    if hit is None:
        return None
    flags = set()
    for needle, flag in FLAG_LINES:
        if (needle in text):
            flags.add(flag)
    return QuestProgress(hit[1], flags)


def read_regicide_progress():
    status = quests.status(REGICIDE)
    if status == 'complete':
        return QuestProgress(RG_STAGE.COMPLETE, set())
    if status != 'in_progress' and status != 'not_started':
        return None
    _w2 = yield from quests.journal(REGICIDE)
    progress = parse_regicide_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress is not None:
        return progress
    return QuestProgress(RG_STAGE.NOT_STARTED, set()) if status == 'not_started' else None

