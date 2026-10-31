"""Ported from rs2b0t's src/bot/api/ai/quests/defs/sheepherder/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.sheepherder.areas import ORDINAL, SHEEP
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests
import _core
from rs2004.quests.engine.types import QuestProgress

__all__ = ['QUEST', 'SH_STAGE', 'parse_sheep_herder_journal', 'read_sheep_herder_progress']

QUEST = 'Sheep Herder'
SH_STAGE = Record({'NOT_STARTED': 0, 'NEED_SUIT': 1, 'DISPOSING': 2, 'COMPLETE': 3})


def all_burnt():
    return set([f'burnt-{n}' for n in SHEEP])


# Why: the journal renders 1 line per sheep, and the 3 it can render (herded, killed, incinerated) are every state the module needs.
# Why: the "killed" line ends on a colour tag before "bones", so no needle may span it.
def sheep_flags(text, n):
    ord = ORDINAL[n]
    if (f'killed the {ord} sheep and incinerated its bones' in text):
        return [f'herded-{n}', f'killed-{n}', f'burnt-{n}']
    if (f'killed the {ord} sheep. now i must incinerate' in text):
        return [f'herded-{n}', f'killed-{n}']
    if (f'herded the {ord} sheep to the pen' in text):
        return [f'herded-{n}']
    return []


def parse_sheep_herder_journal(lines):
    text = normalize(lines)
    if ('quest complete!' in text):
        return QuestProgress(SH_STAGE.COMPLETE, all_burnt())
    if ('i can start this quest by speaking to' in text):
        return QuestProgress(SH_STAGE.NOT_STARTED, set())
    if ('i need to get some protective clothing' in text):
        return QuestProgress(SH_STAGE.NEED_SUIT, set())
    if not ('i bought some protective clothing' in text):
        return None
    # Why: the last page drops the per-sheep lines for one summary, so its own line is the only evidence all 4 are burnt.
    if ('i should return to' in text):
        return QuestProgress(SH_STAGE.DISPOSING, all_burnt())
    flags = set()
    for n in SHEEP:
        for flag in sheep_flags(text, n):
            flags.add(flag)
    return QuestProgress(SH_STAGE.DISPOSING, flags)


def read_sheep_herder_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return QuestProgress(SH_STAGE.COMPLETE, all_burnt())
    if status == 'not_started':
        return QuestProgress(SH_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    progress = parse_sheep_herder_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
