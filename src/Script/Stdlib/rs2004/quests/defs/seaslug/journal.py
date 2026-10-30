"""Ported from rs2b0t's src/bot/api/ai/quests/defs/seaslug/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.tabs import quests
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record
import _core

__all__ = ['QUEST', 'SS_STAGE', 'parse_sea_slug_journal', 'read_sea_slug_progress']

QUEST = 'Sea Slug Quest'
SS_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SPOKEN_HOLGART': 2,
    'BOAT_REPAIRED': 3,
    'SPOKEN_KENNITH': 4,
    'SAILED_KENT': 5,
    'SPOKEN_KENT': 6,
    'LIT_TORCH': 7,
    'KENNITH_NEED_ESCAPE': 8,
    'PANEL_OPENED': 9,
    'NEED_KENNITH_PATH': 10,
    'SAVED_KENNITH': 11,
    'COMPLETE': 12,
})
AMBIGUOUS = {SS_STAGE.SPOKEN_KENNITH: 'kennith-or-kent', SS_STAGE.KENNITH_NEED_ESCAPE: 'panel-or-call'}
MARKERS = [
    Record({'text': 'quest complete!', 'stage': SS_STAGE.COMPLETE}),
    Record({'text': "i've used the crane to lower kennith into the boat", 'stage': SS_STAGE.SAVED_KENNITH}),
    Record({'text': "kennith can't get downstairs without some help", 'stage': SS_STAGE.NEED_KENNITH_PATH}),
    Record({'text': "i've created an opening to let kenneth escape", 'stage': SS_STAGE.KENNITH_NEED_ESCAPE}),
    Record({'text': "kennith won't go near the sea slugs", 'stage': SS_STAGE.LIT_TORCH}),
    Record({'text': "i've found kent on a small island", 'stage': SS_STAGE.SPOKEN_KENT}),
    Record({'text': "i've found kennith", 'stage': SS_STAGE.SPOKEN_KENNITH}),
    Record({'text': 'i gave holgart the swamp paste', 'stage': SS_STAGE.BOAT_REPAIRED}),
    Record({'text': 'his boat is broken', 'stage': SS_STAGE.SPOKEN_HOLGART}),
    Record({'text': 'i need to take the swamp paste to holgart', 'stage': SS_STAGE.SPOKEN_HOLGART}),
    Record({'text': 'i need to talk to holgart', 'stage': SS_STAGE.STARTED}),
    Record({'text': 'i can start this quest by speaking to caroline', 'stage': SS_STAGE.NOT_STARTED}),
]


def progress_for(stage):
    flag = AMBIGUOUS.get(stage)
    return QuestProgress(stage, set(([] if flag is None else [flag])))


def parse_sea_slug_journal(lines):
    text = normalize(lines)
    hit = ([m for m in MARKERS if (m.text in text)] or [None])[0]
    return (progress_for(hit.stage) if hit else None)


def read_sea_slug_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return progress_for(SS_STAGE.COMPLETE)
    if status == 'not_started':
        return progress_for(SS_STAGE.NOT_STARTED)
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    progress = parse_sea_slug_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
