"""Ported from rs2b0t's src/bot/api/ai/quests/defs/treegnome/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests
import _core
from rs2004.quests.engine.types import QuestProgress

__all__ = ['TG_STAGE', 'parse_tree_gnome_journal', 'read_tree_gnome_progress']

TG_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SPOKEN_MONTAI': 2,
    'GAVE_LOGS': 3,
    'FINDING_TRACKERS': 4,
    'BALLISTA_FIRED': 5,
    'RETRIEVED_ORB': 6,
    'RETURNED_FIRST_ORB': 7,
    'DEFEATED_WARLORD': 8,
    'COMPLETE': 9,
})
TREE_GNOME_VILLAGE = 'Tree Gnome Village'
# Why: every stage keeps the past-tense lines of the ones before it, so the highest match names the stage and no needle may span a colour tag.
STAGE_LINES = [
    ['quest complete!', TG_STAGE.COMPLETE],
    ['after a fierce battle i defeated the warlord', TG_STAGE.DEFEATED_WARLORD],
    ['i returned the orb to king bolren', TG_STAGE.RETURNED_FIRST_ORB],
    ['with the stronghold breached', TG_STAGE.RETRIEVED_ORB],
    ['i found the three trackers', TG_STAGE.BALLISTA_FIRED],
    ['now their defences were secure', TG_STAGE.FINDING_TRACKERS],
    ['i brought montai logs', TG_STAGE.GAVE_LOGS],
    ['i spoke to montai', TG_STAGE.SPOKEN_MONTAI],
    ['i spoke to king bolren who told me', TG_STAGE.STARTED],
    ['i can start this quest by speaking to', TG_STAGE.NOT_STARTED],
]


def parse_tree_gnome_journal(lines):
    text = normalize(lines)
    hit = ([entry for entry in STAGE_LINES if entry[0] in text] or [None])[0]
    return (None if hit is None else QuestProgress(hit[1], set()))


def read_tree_gnome_progress():
    status = quests.status(TREE_GNOME_VILLAGE)
    if status == 'complete':
        return QuestProgress(TG_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(TG_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(TREE_GNOME_VILLAGE)
    progress = parse_tree_gnome_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
