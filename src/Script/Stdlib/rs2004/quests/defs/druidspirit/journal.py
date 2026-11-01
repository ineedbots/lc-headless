"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.engine.types import QuestProgress

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.druidspirit.areas import NS_QUEST, NS_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['NS_FLAG', 'parse_druid_journal', 'read_druid_progress']

NS_FLAG = Record({'NATURE': 'nature', 'SPIRIT': 'spirit'})
# Why: `druidspirit_journal.rs2` retains earlier text, so test stage markers newest-first.
MARKERS = [
    ['quest complete!', NS_STAGE.COMPLETE],
    ["i've killed three ghasts now.", NS_STAGE.KILLED_GHAST3],
    ["i've killed two ghasts now.", NS_STAGE.KILLED_GHAST2],
    ['the druid pouch made a ghast appear', NS_STAGE.KILLED_GHAST1],
    ['them into a druid pouch', NS_STAGE.ADDED_POUCH],
    ['i collected some bloomed items from the swamp.', NS_STAGE.PICKED_SICKLE],
    ['i cast the bloom spell in the swamp.', NS_STAGE.CASTED_SICKLE_BLOOM],
    ['filliman has blessed the silver sickle for me.', NS_STAGE.BLESSED_SICKLE],
    ['filliman has turned into a nature spirit', NS_STAGE.FULL_TRANSFORM],
    ['i entered fillimans grotto as he asked me to.', NS_STAGE.ENTERED_GROTTO],
    ['he says that he can cast the spell now', NS_STAGE.PERFORMED_RITUAL],
    ['i collected a mort myre fungi.', NS_STAGE.PICKED_FUNGI],
    ["i've cast the bloom spell in the swamp.", NS_STAGE.CASTED_SPELL],
    ["i've been blessed at the temple by drezel.", NS_STAGE.BLESSED],
    ['spell but i need to be', NS_STAGE.RECEIVED_SPELL],
    ['might need my help with his plan', NS_STAGE.GIVEN_JOURNAL],
    ['to find his journal', NS_STAGE.SHOWN_MIRROR],
    ["i've found filliman's journal", NS_STAGE.SHOWN_MIRROR],
    ['convince this poor fellow', NS_STAGE.SPOKEN_FILLIMAN],
    ["i can't really communicate with this", NS_STAGE.FAILED_TALK],
    ['i need to look for filliman tarlock', NS_STAGE.STARTED],
    ['i can start this quest by speaking to', NS_STAGE.NOT_STARTED],
]


def parse_druid_journal(lines):
    text = normalize(lines)
    hit = ([marker for marker in MARKERS if marker[0] in text] or [None])[0]
    if not hit:
        return None
    stage = hit[1]
    flags = set()
    if ('absorbed into the nature stone' in text):
        flags.add(NS_FLAG.NATURE)
    if ('absorbed into the spirit stone' in text):
        flags.add(NS_FLAG.SPIRIT)
    # Why: the stone lines are written at stages 50 and 55 alone; past the ritual both are facts the page stops stating.
    if stage >= NS_STAGE.PERFORMED_RITUAL:
        flags.add(NS_FLAG.NATURE)
        flags.add(NS_FLAG.SPIRIT)
    return QuestProgress(stage, flags)


last_good = None


def read_druid_progress():
    global last_good
    status = quests.status(NS_QUEST)
    if status == 'complete':
        return QuestProgress(NS_STAGE.COMPLETE, set([NS_FLAG.NATURE, NS_FLAG.SPIRIT]))
    if status == 'not_started':
        return QuestProgress(NS_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(NS_QUEST)
    progress = parse_druid_journal(lines)
    # Why: the swamp gate's refusal is a mesbox on main, and while one is up every journal read comes back empty.
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
