"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dwarfcannon/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests
import _core
from rs2004.quests.engine.types import QuestProgress

__all__ = ['MC_STAGE', 'MCANNON_QUEST', 'MC_FLAG', 'parse_dwarf_cannon_journal', 'read_dwarf_cannon_progress']

# Why: stages 6 and 7 render identical journal text and the same step drives both: at 6 the first Inspect flips to 7, at 7 Inspect opens the repair menu.
MC_STAGE = Record({
    'NOT_STARTED': 0,
    'RAILINGS': 1,
    'GUARD_TOWER': 2,
    'GOBLIN_CAVE': 3,
    'FIND_CHILD': 4,
    'CHILD_RESCUED': 5,
    'FIX_CANNON': 6,
    'CANNON_FIXED': 8,
    'SEE_NULODION': 9,
    'RETURN_NOTES': 10,
    'COMPLETE': 11,
})
MCANNON_QUEST = 'Dwarf Cannon'
MC_FLAG = Record({'RAILINGS_DONE': 'railings-done', 'HAS_REMAINS': 'has-remains'})


def read_flags(text):
    flags = set()
    if ('repaired all the broken railings' in text):
        flags.add(MC_FLAG.RAILINGS_DONE)
    if ('found some dwarf remains' in text):
        flags.add(MC_FLAG.HAS_REMAINS)
    return flags


def read_stage(text):
    # Newest first; later journal text keeps earlier history, and the guard-tower page still carries the railings line.
    if ('quest complete!' in text):
        return MC_STAGE.COMPLETE
    if ('gave me an ammo mould and notes' in text):
        return MC_STAGE.RETURN_NOTES
    if ('asked me to find nulodion' in text):
        return MC_STAGE.SEE_NULODION
    if ('fixed the broken multicannon' in text):
        return MC_STAGE.CANNON_FIXED
    if ('asked me to fix the multicannon' in text):
        return MC_STAGE.FIX_CANNON
    if ('rescued the dwarf child' in text):
        return MC_STAGE.CHILD_RESCUED
    if ('next i need to find the' in text):
        return MC_STAGE.FIND_CHILD
    if ('sent me to find the goblin base' in text):
        return MC_STAGE.GOBLIN_CAVE
    if ('check up on his guards' in text) or ('i went to the watchtower' in text):
        return MC_STAGE.GUARD_TOWER
    if ('my first task is to' in text) or ('repaired all the broken railings' in text):
        return MC_STAGE.RAILINGS
    if ('i can start this quest' in text):
        return MC_STAGE.NOT_STARTED
    return None


def parse_dwarf_cannon_journal(lines):
    """Journal text to varp-aligned stages plus sub-progress flags."""
    text = normalize(lines)
    stage = read_stage(text)
    return (None if stage is None else QuestProgress(stage, read_flags(text)))


def read_dwarf_cannon_progress():
    status = quests.status(MCANNON_QUEST)
    if status == 'complete':
        return QuestProgress(MC_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(MC_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(MCANNON_QUEST)
    progress = parse_dwarf_cannon_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
