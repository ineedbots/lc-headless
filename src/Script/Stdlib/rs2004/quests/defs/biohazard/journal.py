"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['BIO_STAGE', 'parse_biohazard_journal', 'read_biohazard_progress']

BIO_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SPOKEN_JERICO': 2,
    'USED_BIRDFEED': 3,
    'RELEASED_PIGEONS': 4,
    'CLIMBED_LADDER': 5,
    'POISONED_STEW': 6,
    'FOUND_DISTILLATOR': 7,
    'GIVEN_DISTILLATOR': 10,
    'SPOKEN_CHEMIST': 12,
    'FOUND_SECRET': 14,
    'REPORTED_ELENA': 15,
    'COMPLETE': 16,
})
BIOHAZARD = 'Biohazard'
# Why: the journal appends, so every line from an earlier stage is still on the page; the most advanced match wins and this order is the test order.
STAGE_LINES = [
    ['quest complete!', BIO_STAGE.COMPLETE],
    ['i need to confront the', BIO_STAGE.REPORTED_ELENA],
    ['findings were very interesting', BIO_STAGE.FOUND_SECRET],
    ["i've given all the items to guidor", BIO_STAGE.FOUND_SECRET],
    ['the varrock guards are out looking for someone', BIO_STAGE.SPOKEN_CHEMIST],
    ['elena gave me some chemicals to take to guidor', BIO_STAGE.SPOKEN_CHEMIST],
    ["elena's asked me to take the following items to", BIO_STAGE.GIVEN_DISTILLATOR],
    ["i've found elena's distillator and returned it to her", BIO_STAGE.GIVEN_DISTILLATOR],
    ["i managed to find elena's distillator", BIO_STAGE.FOUND_DISTILLATOR],
    ["i have rather unkindly poisoned the mourners' stew", BIO_STAGE.POISONED_STEW],
    ["i've crossed the wall into west ardougne", BIO_STAGE.CLIMBED_LADDER],
    ['the watch tower is now surrounded by flapping pigeons', BIO_STAGE.RELEASED_PIGEONS],
    ["i've chucked some birdfeed onto the watch tower", BIO_STAGE.USED_BIRDFEED],
    ['will be able to get me over the wall', BIO_STAGE.SPOKEN_JERICO],
    ["i've spoken to jerico about getting into west ardougne", BIO_STAGE.SPOKEN_JERICO],
    ['about getting over the wall', BIO_STAGE.STARTED],
    ['i can start this quest by speaking to', BIO_STAGE.NOT_STARTED],
]


def parse_biohazard_journal(lines):
    text = normalize(lines)
    hit = ([line for line in STAGE_LINES if line[0] in text] or [None])[0]
    return None if hit is None else QuestProgress(hit[1], set())


def read_biohazard_progress():
    status = quests.status(BIOHAZARD)
    if status == 'complete':
        return QuestProgress(BIO_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(BIO_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(BIOHAZARD)
    progress = parse_biohazard_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
