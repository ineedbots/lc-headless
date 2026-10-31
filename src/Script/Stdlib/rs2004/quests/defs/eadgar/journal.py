"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.trollstronghold.journal import TROLL_FLAG, TROLL_QUEST, parse_troll_stronghold_journal
from rs2004.quests.engine.types import QuestProgress, has_flag
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['EADGAR_STAGE', 'EADGAR_QUEST', 'EADGAR_FLAG', 'SCARECROW_NEED', 'parse_eadgar_journal', 'mark_eadgar_freed', 'read_eadgar_progress']

EADGAR_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 10,
    'SPOKE_EADGAR': 15,
    'SPOKE_BURNTMEAT_FIRST': 20,
    'SPOKE_BURNTMEAT': 25,
    'NEEDS_PARROT': 30,
    'EXPLAINED_PLAN': 50,
    'HID_PARROT': 60,
    'NEEDS_ITEMS': 70,
    'NEEDS_POTION': 80,
    'NEEDS_PARROT_BACK': 85,
    'GOT_PARROT_BACK': 86,
    'GOT_FAKE_MAN': 87,
    'GOT_BURNT_MEAT': 90,
    'UNLOCKED_STOREROOM': 100,
    'COMPLETE': 110,
})
EADGAR_QUEST = "Eadgar's Ruse"
EADGAR_FLAG = Record({
    'NEED_LOGS': 'need-logs',
    'NEED_CHICKENS': 'need-chickens',
    'NEED_GRAIN': 'need-grain',
    'NEED_CLOTHES': 'need-clothes',
    'POTION_MADE': 'potion-made',
    'HAVE_GOUTWEED': 'have-goutweed',
    'EADGAR_FREED': 'eadgar-freed',
})
SCARECROW_NEED = Record({'logs': 1, 'chickens': 5, 'grain': 10, 'clothes': 1})


# pocketpy has no re: the number written just before one of the phrases, as rs2b0t's /(\d+) phrase/ captures it.
def count_before(text, phrases):
    for phrase in phrases:
        at = text.find(' ' + phrase)
        if at < 0:
            continue
        start = at
        while start > 0 and text[start - 1] >= '0' and text[start - 1] <= '9':
            start -= 1
        if start < at:
            return text[start:at]
    return None


# Why: the needs list repeats words the struck-through history also uses, so it is read from the tail after "i still need to bring him:".
def read_needs(text):
    flags = set()
    at = text.find('i still need to bring him')
    if at < 0:
        return flags
    tail = text[at:]
    if 'logs' in tail.split():
        flags.add(EADGAR_FLAG.NEED_LOGS)
    chickens = count_before(tail, ['raw chicken'])
    if chickens:
        flags.add(f'{EADGAR_FLAG.NEED_CHICKENS}:{chickens}')
    grain = count_before(tail, ['sheaves of grains', 'sheaf of grain'])
    if grain:
        flags.add(f'{EADGAR_FLAG.NEED_GRAIN}:{grain}')
    if ('some dirty clothes' in tail):
        flags.add(EADGAR_FLAG.NEED_CLOTHES)
    return flags


def read_flags(text, stage):
    flags = (read_needs(text) if stage == EADGAR_STAGE.NEEDS_ITEMS else set())
    if ('i made the troll potion. i should go give it' in text):
        flags.add(EADGAR_FLAG.POTION_MADE)
    if ('i snuck into the storeroom and got some goutweed' in text):
        flags.add(EADGAR_FLAG.HAVE_GOUTWEED)
    return flags


# Why: the journal keeps every earlier line struck through, so the newest phrase has to match first.
def read_stage(text):
    if ('quest complete!' in text):
        return EADGAR_STAGE.COMPLETE
    if ("i've unlocked the storeroom" in text):
        return EADGAR_STAGE.UNLOCKED_STOREROOM
    if ('key to the storeroom is in a' in text):
        return EADGAR_STAGE.GOT_BURNT_MEAT
    if ("i got eadgar's fake man" in text):
        return EADGAR_STAGE.GOT_FAKE_MAN
    if ('i fetched the parrot back from the troll prison rack' in text):
        return EADGAR_STAGE.GOT_PARROT_BACK
    if ('i made the troll potion and gave it to mad eadgar' in text):
        return EADGAR_STAGE.NEEDS_PARROT_BACK
    if ('i gave eadgar everything he needed' in text):
        return EADGAR_STAGE.NEEDS_POTION
    if ('i still need to bring him' in text):
        return EADGAR_STAGE.NEEDS_ITEMS
    if ('i hid the parrot under the rack in the troll prison' in text):
        return EADGAR_STAGE.HID_PARROT
    if ('i got the parrot eadgar wanted' in text):
        return EADGAR_STAGE.EXPLAINED_PLAN
    if ('mad eadgar has a plan' in text):
        return EADGAR_STAGE.NEEDS_PARROT
    if ('the troll cook will tell me how to find goutweed' in text):
        return EADGAR_STAGE.SPOKE_BURNTMEAT
    if ('i should ask the troll cook' in text):
        return EADGAR_STAGE.SPOKE_EADGAR
    if ('sanfew asked me to find him some goutweed' in text):
        return EADGAR_STAGE.STARTED
    if ('i can start this quest' in text):
        return EADGAR_STAGE.NOT_STARTED
    return None


def parse_eadgar_journal(lines):
    """Map quest-list journal text to varp-aligned stages plus sub-progress flags."""
    text = normalize(lines)
    stage = read_stage(text)
    if stage is None:
        return None
    return QuestProgress(stage, read_flags(text, stage))


def close_journal():
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)


# Why: Troll Stronghold can be finished without opening Mad Eadgar's cell, and an unfreed Eadgar leaves the Cave Entrance dropping you into an empty room.
# Why: the completed Troll Stronghold journal still records it, "I've rescued Godric and Mad Eadgar."
# Why: it is read once and cached, as every read opens and closes the quest-list modal.
freed_cache = None


def mark_eadgar_freed():
    """Called by the recovery that opens the cell, so the journal is not read again."""
    global freed_cache
    freed_cache = True


def troll_freed_eadgar():
    global freed_cache
    if freed_cache is not None:
        return freed_cache
    status = quests.status(TROLL_QUEST)
    if status != 'complete' and status != 'in_progress':
        return False
    _w1 = yield from quests.journal(TROLL_QUEST)
    progress = parse_troll_stronghold_journal(_w1)
    yield from close_journal()
    freed_cache = has_flag(progress, TROLL_FLAG.FREED_EADGAR)
    return freed_cache


def read_eadgar_progress():
    status = quests.status(EADGAR_QUEST)
    if status == 'complete':
        return QuestProgress(EADGAR_STAGE.COMPLETE, set())
    if status != 'in_progress' and status != 'not_started':
        return None
    freed = yield from troll_freed_eadgar()
    if status == 'not_started':
        return QuestProgress(EADGAR_STAGE.NOT_STARTED, (set([EADGAR_FLAG.EADGAR_FREED]) if freed else set()))
    _w2 = yield from quests.journal(EADGAR_QUEST)
    progress = parse_eadgar_journal(_w2)
    yield from close_journal()
    if not progress:
        return None
    flags = set(progress.flags)
    if freed:
        flags.add(EADGAR_FLAG.EADGAR_FREED)
    return QuestProgress(progress.stage, flags)
