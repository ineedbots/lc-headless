"""Ported from rs2b0t's src/bot/api/ai/quests/defs/knightssword/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.interfaces import interfaces
from rs2004.quests.defs.knightssword.areas import KS_QUEST, KS_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests


__all__ = ['parse_knights_sword_journal', 'read_knights_sword_progress']

def read_stage(text):
    """Newest marker first: squire_journal.rs2 appends, so earlier stages' prose is still on the scroll."""
    if ('quest complete!' in text):
        return KS_STAGE.COMPLETE
    if ('thurgo has now smithed me a replica' in text):
        return KS_STAGE.LOOKING_BLURITE
    if ('according to thurgo to make a replica sword' in text):
        return KS_STAGE.LOOKING_BLURITE
    if ('the squire told me about a' in text):
        return KS_STAGE.LOOKING_PORTRAIT
    if ('needs a picture of the sword before he can help' in text):
        return KS_STAGE.SPOKEN_THURGO
    if ('gained his trust through' in text):
        return KS_STAGE.GIVEN_PIE
    if ("reldo couldn't give me much information" in text):
        return KS_STAGE.SPOKEN_RELDO
    if ('the squire suggests i speak to' in text):
        return KS_STAGE.STARTED
    if ('i can start this quest by talking to the' in text):
        return KS_STAGE.NOT_STARTED
    return None


def parse_knights_sword_journal(lines):
    stage = read_stage(normalize(lines))
    return (None if stage is None else Record({'stage': stage, 'flags': set()}))


last_good = None


def read_knights_sword_progress():
    global last_good
    status = quests.status(KS_QUEST)
    if status == 'complete':
        return Record({'stage': KS_STAGE.COMPLETE, 'flags': set()})
    if status == 'not_started':
        return Record({'stage': KS_STAGE.NOT_STARTED, 'flags': set()})
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(KS_QUEST)
    progress = parse_knights_sword_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
