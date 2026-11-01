"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['UP_STAGE', 'UP_FLAG', 'UPASS', 'parse_upass_journal', 'read_upass_progress']

# Why: these are the `%upass` values themselves, so `--stage N` in the harness and the module's stage are one scale. "Started" is bit 11 of `%ibanmulti`, carried as a flag.
UP_STAGE = Record({
    'NOT_STARTED': 0,
    'SPOKEN_KOFTIK': 1,
    'PASSED_BRIDGE': 2,
    'ENTERED_SECOND_AREA': 3,
    'KILLED_UNICORN': 4,
    'ENTERED_MAIN_AREA': 5,
    'SPOKEN_NILHOOF': 6,
    'FOUND_DOLL': 7,
    'CONFRONTED_IBAN': 8,
    'DEFEATED_IBAN': 9,
    'COMPLETE': 10,
})
UP_FLAG = Record({
    'STARTED': 'started',
    'ARROW_PARTS': 'arrowParts',
    'RANDAS_DIARY': 'randasDiary',
    'WELL_INSCRIPTION': 'wellInscription',
    'KOFTIK_INSANE': 'koftikInsane',
    'ASHES_ON_DOLL': 'ashesOnDoll',
    'BLOOD_ON_DOLL': 'bloodOnDoll',
    'SHADOW_ON_DOLL': 'shadowOnDoll',
    'DOVE_ON_DOLL': 'doveOnDoll',
    'DOLL_COMPLETE': 'dollComplete',
})
UPASS = 'Underground Pass'
# Why: the journal is additive, every stage keeps the earlier lines and appends its own, so the deepest matching line wins and the list runs from the end of the quest backwards.
STAGE_LINES = [
    ['quest complete!', UP_STAGE.COMPLETE],
    ['throwing iban', UP_STAGE.DEFEATED_IBAN],
    ['after distracting the witch', UP_STAGE.FOUND_DOLL],
    ['the group leader said', UP_STAGE.SPOKEN_NILHOOF],
    ['pass through the double doors', UP_STAGE.ENTERED_MAIN_AREA],
    ["i must 'feed' it", UP_STAGE.KILLED_UNICORN],
    ['something is watching me', UP_STAGE.ENTERED_SECOND_AREA],
    ['after destroying four orbs', UP_STAGE.PASSED_BRIDGE],
    ['i managed to cross the bridge', UP_STAGE.PASSED_BRIDGE],
    ['i have met koftik at an underground river', UP_STAGE.SPOKEN_KOFTIK],
    ['i have met koftik', UP_STAGE.SPOKEN_KOFTIK],
    ['asked me to meet a tracker named koftik', UP_STAGE.NOT_STARTED],
    ['i can start this quest', UP_STAGE.NOT_STARTED],
]
FLAG_LINES = [
    ['asked me to meet a tracker named koftik', UP_FLAG.STARTED],
    ['charred remains of some arrows', UP_FLAG.ARROW_PARTS],
    ['it tells of a well that i must enter', UP_FLAG.RANDAS_DIARY],
    ["an inscription says that i must 'feed'", UP_FLAG.WELL_INSCRIPTION],
    ['i fear for his sanity', UP_FLAG.KOFTIK_INSANE],
    ['i rubbed some of the ash into the doll', UP_FLAG.ASHES_ON_DOLL],
    ['smear some of its fluids onto the doll', UP_FLAG.BLOOD_ON_DOLL],
    ["the doll now has iban's shadow", UP_FLAG.SHADOW_ON_DOLL],
    ["imbued it with iban's conscience", UP_FLAG.DOVE_ON_DOLL],
    ['i have completed the doll', UP_FLAG.DOLL_COMPLETE],
]


def parse_upass_journal(lines):
    """Stage plus sub-progress from the journal text. Why: `%upass` and `%ibanmulti` are both `scope=perm` with no `transmit`, so the journal scroll is the only client-visible record of either."""
    text = normalize(lines)
    hit = ([(needle, _2) for needle, _2 in STAGE_LINES if (needle in text)] or [None])[0]
    if hit is None:
        return None
    flags = set()
    for needle, flag in FLAG_LINES:
        if (needle in text):
            flags.add(flag)
    # Why: the journal only prints "confronted" progress as the doll lines, so FOUND_DOLL and CONFRONTED_IBAN read the same with a complete doll; the module resolves the rest from the pack.
    return QuestProgress(hit[1], flags)


def read_upass_progress():
    status = quests.status(UPASS)
    if status == 'complete':
        return QuestProgress(UP_STAGE.COMPLETE, set())
    if status != 'in_progress' and status != 'not_started':
        return None
    _w2 = yield from quests.journal(UPASS)
    progress = parse_upass_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress is not None:
        return progress
    return QuestProgress(UP_STAGE.NOT_STARTED, set()) if status == 'not_started' else None

