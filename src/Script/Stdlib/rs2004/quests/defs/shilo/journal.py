"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.engine.types import QuestProgress

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['SHILO_QUEST', 'SV_STAGE', 'parse_shilo_journal', 'read_shilo_progress']

SHILO_QUEST = 'Shilo Village'
# Why: stages 1-2, 7-9 (before the Bervirius dolmen), 10-11 and 12-14 render identically, so `decide()` separates them by area and what is carried.
SV_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SEARCHED_MOUND': 3,
    'DUG_MOUND': 4,
    'LIT_MOUND': 5,
    'ROPED_MOUND': 6,
    'ENTERED_AH_ZA_RHOON': 7,
    'UNLOCKED_RASH_TOMB': 10,
    'UNLOCKED_TOMBDOOR': 12,
    'COMPLETE': 15,
})
# Needles avoid anything a colour tag sits next to: stripping "@dre@" leaves a space, so "'@dre@Ah Za Rhoon@dbl@'" normalises to "' ah za rhoon '".
STAGE_LINES = [
    ['quest complete!', SV_STAGE.COMPLETE],
    ["i've placed three bones", SV_STAGE.UNLOCKED_TOMBDOOR],
    ['i made a bone key from the bone shard', SV_STAGE.UNLOCKED_RASH_TOMB],
    ['i climbed down the rope', SV_STAGE.ENTERED_AH_ZA_RHOON],
    ['i attached a rope to the start of the fissure', SV_STAGE.ROPED_MOUND],
    ['i illuminated the fissure', SV_STAGE.LIT_MOUND],
    ['used a spade to excavate', SV_STAGE.DUG_MOUND],
    ["i've found a mound of earth", SV_STAGE.SEARCHED_MOUND],
    ['i need to find the location of', SV_STAGE.STARTED],
    ['i can start this quest', SV_STAGE.NOT_STARTED],
]
FLAG_LINES = [
    ["i've read the tattered scroll", 'read-tattered'],
    ['i read the crumpled scroll', 'read-crumpled'],
    ['the lock is made out of bone', 'found-door'],
    ['i searched the dolmen in bervirius tomb', 'pommel-taken'],
]


def read_flags(text):
    flags = set()
    for needle, flag in FLAG_LINES:
        if (needle in text):
            flags.add(flag)
    if ("i've placed three bones" in text):
        flags.add('bones-placed:3')
    elif ("i've placed two bones" in text):
        flags.add('bones-placed:2')
    else:
        if ("i've placed one bone" in text):
            flags.add('bones-placed:1')
        else:
            flags.add('bones-placed:0')
    # The 3 kill paragraphs are cumulative rewrites.
    if ('third and final guardian' in text):
        flags.add('naza:3')
    elif ('a skeletal nazastarool appeared' in text):
        flags.add('naza:2')
    else:
        if ('a zombie nazastarool attacked me' in text):
            flags.add('naza:1')
        else:
            flags.add('naza:0')
    return flags


def parse_shilo_journal(lines):
    text = normalize(lines)
    # Newest first: every later entry keeps the earlier history.
    hit = ([line for line in STAGE_LINES if line[0] in text] or [None])[0]
    return (QuestProgress(hit[1], read_flags(text)) if hit else None)


def read_shilo_progress():
    status = quests.status(SHILO_QUEST)
    if status == 'complete':
        return QuestProgress(SV_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(SV_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(SHILO_QUEST)
    progress = parse_shilo_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
