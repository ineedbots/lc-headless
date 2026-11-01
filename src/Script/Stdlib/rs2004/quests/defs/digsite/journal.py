"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.digsite.areas import DIG_NAME
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal
from rs2004.tabs import quests

__all__ = ['DIG_STAGE', 'parse_digsite_journal', 'reset_digsite_journal_cache', 'read_digsite_progress']

DIG_STAGE = Record({
    'NOT_STARTED': 0,
    'STAMPING': 1,
    'FIRST_EXAM': 2,
    'SECOND_EXAM': 3,
    'THIRD_EXAM': 4,
    'IMPRESS_EXPERT': 5,
    'MINESHAFT_PERMIT': 6,
    'POURED_COMPOUND': 7,
    'REMOVED_BLOCKAGE': 8,
    'COMPLETE': 9,
})


# Why: Keep the leading space because "She gave me an answer" contains the other marker without it.
def normalize(lines):
    return ' ' + normalize_journal(lines)


# Why: earlier lines stay on the page struck through with the same words, so this order is what separates a finished leg from the current one.
STAGES = [
    ['quest complete!', DIG_STAGE.COMPLETE],
    ['interesting find in the secret room', DIG_STAGE.REMOVED_BLOCKAGE],
    ['ignite the explosive compound', DIG_STAGE.POURED_COMPOUND],
    ['move the rocks blocking the way', DIG_STAGE.MINESHAFT_PERMIT],
    ['letter to a workman near a', DIG_STAGE.IMPRESS_EXPERT],
    ['study for my third exam', DIG_STAGE.THIRD_EXAM],
    ['study for my second exam', DIG_STAGE.SECOND_EXAM],
    ['study for my first exam', DIG_STAGE.FIRST_EXAM],
    ['curator of the varrock museum', DIG_STAGE.STAMPING],
    ['i can start this quest by speaking to', DIG_STAGE.NOT_STARTED],
]
FLAGS = [
    ['i should talk to the examiner to take my', 'exam-ready'],
    ['green top about the exams. he gave me an answer', 'green-answered'],
    ['orange top about the exams. he gave me an answer', 'orange-answered'],
    ['she gave me an answer', 'purple-answered'],
    ['i need to bring her an opal', 'opal-wanted'],
]
ANSWERED_LINE = ' he gave me an answer'


def count_of(text, needle):
    count = 0
    i = text.find(needle)
    while i != -1:
        count += 1
        i = text.find(needle, i + len(needle))
    return count


def parse_digsite_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    stage = None
    for needle, candidate in STAGES:
        if needle in text:
            stage = candidate
            break
    if stage is None:
        return None
    flags = set()
    for needle, flag in FLAGS:
        if (needle in text):
            flags.add(flag)
    # Why: both answered lines read the same, so two of them is proof of both even if the pair ordering ever changes.
    if count_of(text, ANSWERED_LINE) >= 2:
        flags.add('green-answered')
        flags.add('orange-answered')
    return QuestProgress(stage, flags)


last_good = None


def reset_digsite_journal_cache():
    """Test seam: the last good page is memoised for the process."""
    global last_good
    last_good = None


def read_digsite_progress():
    global last_good
    status = quests.status(DIG_NAME)
    if status == 'complete':
        return QuestProgress(DIG_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(DIG_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(DIG_NAME)
    progress = parse_digsite_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
