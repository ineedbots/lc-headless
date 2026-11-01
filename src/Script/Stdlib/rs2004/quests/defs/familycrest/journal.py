"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.familycrest.areas import FC_QUEST, FC_STAGE
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['parse_family_crest_journal', 'journal_read', 'describe_journal', 'read_family_crest_progress']

def read_stage(text):
    """Newest marker first: crest_journal.rs2 appends, so earlier prose is still on the scroll."""
    if ('quest complete!' in text):
        return FC_STAGE.COMPLETE
    if ('lost his piece of the family crest to a demon' in text):
        return FC_STAGE.CURED_JOHNATHON
    if ('he soon recovered when i used an antipoison' in text):
        return FC_STAGE.CURED_JOHNATHON
    if ('looking very ill at the jolly boar inn' in text):
        return FC_STAGE.SPOKEN_JOHNATHON
    if ('final crest piece is with their brother' in text):
        return FC_STAGE.AVAN_PIECE
    if ('gave me his crest piece in return for a ruby ring' in text):
        return FC_STAGE.AVAN_PIECE
    if ('will give me his crest piece if i can bring him a ruby' in text):
        return FC_STAGE.SPOKEN_BOOT
    if ('i should find a dwarf named' in text):
        return FC_STAGE.SPOKEN_AVAN
    if ('told me that avan is wearing a' in text):
        return FC_STAGE.SPOKEN_GEM_TRADER
    if ('is on a treasure hunt in the' in text):
        return FC_STAGE.CALEB_WHERE
    if ('crest piece, i need to find the other' in text):
        return FC_STAGE.CALEB_PIECE
    if ('will let me have his piece in return for' in text):
        return FC_STAGE.SPOKEN_CALEB
    if ('i need to find his son' in text):
        return FC_STAGE.SPOKEN_DIMINTHEIS
    if ('i can start this quest' in text):
        return FC_STAGE.NOT_STARTED
    return None


def parse_family_crest_journal(lines):
    stage = read_stage(normalize(lines))
    return None if stage is None else QuestProgress(stage, set())


last_good = None
journal_read = Record({'reads': 0, 'failures': 0, 'cached': False})


def describe_journal():
    stage = journal_read.stage
    cached = journal_read.cached
    failures = journal_read.failures
    reads = journal_read.reads
    shown = stage if stage is not None else '?'
    note = ' (CACHED — this read failed)' if cached else ''
    counts = f' reads={reads} failures={failures}' if failures > 0 else ''
    return f'stage={shown}{note}{counts}'


def read_family_crest_progress():
    global last_good
    status = quests.status(FC_QUEST)
    if status == 'complete':
        return QuestProgress(FC_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(FC_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(FC_QUEST)
    progress = parse_family_crest_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    journal_read.reads += 1
    journal_read.cached = progress is None
    if progress:
        last_good = progress
    else:
        journal_read.failures += 1
    used = (progress if progress is not None else last_good)
    journal_read.stage = (used.stage if used is not None else None)
    return used
