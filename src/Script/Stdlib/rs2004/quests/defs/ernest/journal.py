"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ernest/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.interfaces import interfaces
from rs2004.quests.defs.ernest.areas import EC_QUEST, EC_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests


__all__ = ['parse_ernest_journal', 'read_ernest_progress']

def read_stage(text):
    """haunted_journal.rs2 writes one self-contained block per stage, but newest-first still holds and matches every other module."""
    if ('we turned ernest back to normal' in text):
        return EC_STAGE.COMPLETE
    if ('discovered ernest is a' in text):
        return EC_STAGE.SPOKEN_ODDENSTEIN
    if ('he went into' in text):
        return EC_STAGE.STARTED
    if ('i can start this quest by speaking to' in text):
        return EC_STAGE.NOT_STARTED
    return None


def parse_ernest_journal(lines):
    stage = read_stage(normalize(lines))
    return (None if stage is None else Record({'stage': stage, 'flags': set()}))


last_good = None


def read_ernest_progress():
    global last_good
    status = quests.status(EC_QUEST)
    if status == 'complete':
        return Record({'stage': EC_STAGE.COMPLETE, 'flags': set()})
    if status == 'not_started':
        return Record({'stage': EC_STAGE.NOT_STARTED, 'flags': set()})
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(EC_QUEST)
    progress = parse_ernest_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
