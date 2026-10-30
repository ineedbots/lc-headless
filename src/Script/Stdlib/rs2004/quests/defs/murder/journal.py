"""Ported from rs2b0t's src/bot/api/ai/quests/defs/murder/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.tabs import quests
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.quests.defs.murder.areas import MURDER_NAME
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record
import _core

__all__ = ['MURDER_STAGE', 'POISON_PROVED', 'THREAD_FOUND', 'WEAPON_TAKEN', 'parse_murder_journal', 'read_murder_progress', 'reset_murder_progress_cache']

MURDER_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'COMPLETE': 2})
POISON_PROVED = 'poison-proved'
THREAD_FOUND = 'thread'
WEAPON_TAKEN = 'weapon'
STAGES = [
    ['quest complete!', MURDER_STAGE.COMPLETE],
    ['lord sinclair, a prominent nobleman', MURDER_STAGE.STARTED],
    ['i can start this quest by speaking to', MURDER_STAGE.NOT_STARTED],
]
FLAGS = [
    ['indisputable evidence', POISON_PROVED],
    ['i have found some coloured thread', THREAD_FOUND],
    ['i have taken the murder weapon', WEAPON_TAKEN],
]


def parse_murder_journal(lines):
    text = normalize(lines)
    hit = ([entry for entry in STAGES if entry[0] in text] or [None])[0]
    if not hit:
        return None
    flags = set()
    for needle, flag in FLAGS:
        if (needle in text):
            flags.add(flag)
    return QuestProgress(hit[1], flags)


# Why: the page drops every in-progress line once the poison is proved, so a stale read doesn't mean the quest went backwards.
last_good = None


def read_murder_progress():
    global last_good
    status = quests.status(MURDER_NAME)
    if status == 'complete':
        return QuestProgress(MURDER_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(MURDER_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(MURDER_NAME)
    progress = parse_murder_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)


def reset_murder_progress_cache():
    global last_good
    """Test seam: the last good read is memoised for the process."""
    last_good = None
