"""Ported from rs2b0t's src/bot/api/ai/quests/defs/trollstronghold/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['TROLL_STAGE', 'TROLL_QUEST', 'TROLL_FLAG', 'parse_troll_stronghold_journal', 'read_troll_stronghold_progress']

TROLL_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 10,
    'DEFEATED_DAD': 20,
    'ENTERED_PRISON': 30,
    'FREED_GODRIC': 40,
    'COMPLETE': 50,
})
TROLL_QUEST = 'Troll Stronghold'
TROLL_FLAG = Record({
    'BOOTS': 'boots',
    'ENTERED_STRONGHOLD': 'entered-stronghold',
    'HAS_PRISON_KEY': 'has-prison-key',
    'FREED_EADGAR': 'freed-eadgar',
})


def read_flags(text):
    flags = set()
    if ('climbing boots from tenzing' in text):
        flags.add(TROLL_FLAG.BOOTS)
    if ('found my way into the troll stronghold' in text):
        flags.add(TROLL_FLAG.ENTERED_STRONGHOLD)
    if ('i have the prison key' in text):
        flags.add(TROLL_FLAG.HAS_PRISON_KEY)
    # Stage 30 prints "I've rescued Mad Eadgar."; stage 40 folds him into "I've rescued Godric and Mad Eadgar.", so match both.
    if ('rescued mad eadgar' in text) or ('and mad eadgar' in text):
        flags.add(TROLL_FLAG.FREED_EADGAR)
    return flags


def read_stage(text):
    # Newest progress first, later journal text retains earlier history.
    if ('quest complete!' in text):
        return TROLL_STAGE.COMPLETE
    if ("i've rescued godric" in text) or ('rescued godric' in text) or ('return and tell dunstan' in text) or ('law talisman' in text):
        # Complete text also mentions the law talisman; COMPLETE already matched above.
        if ('i talked to dunstan and he gave me the law talisman' in text):
            return TROLL_STAGE.COMPLETE
        return TROLL_STAGE.FREED_GODRIC
    if ('found my way into the prison' in text) or ('i have to rescue godric' in text):
        return TROLL_STAGE.ENTERED_PRISON
    if ('defeated the troll champion' in text) or ('find a way to get into the troll stronghold' in text) or ('find a way to get into the prison' in text) or ('i have the prison key' in text):
        return TROLL_STAGE.DEFEATED_DAD
    if ('promised denulth' in text) or ('rescue godric from the troll stronghold' in text) or ('defeat the troll champion' in text) or ("accepted the troll champion's challenge" in text):
        return TROLL_STAGE.STARTED
    if ('i can start this quest' in text):
        return TROLL_STAGE.NOT_STARTED
    return None


def parse_troll_stronghold_journal(lines):
    """Map quest-list journal text to varp-aligned stages + sub-progress flags."""
    text = normalize(lines)
    stage = read_stage(text)
    if stage is None:
        return None
    return QuestProgress(stage, read_flags(text))


def read_troll_stronghold_progress():
    status = quests.status(TROLL_QUEST)
    if status == 'complete':
        return QuestProgress(TROLL_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(TROLL_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(TROLL_QUEST)
    progress = parse_troll_stronghold_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
