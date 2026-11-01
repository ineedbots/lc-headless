"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['WATCHTOWER_STAGE', 'WATCHTOWER_QUEST', 'parse_watchtower_journal', 'read_watchtower_progress']

WATCHTOWER_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'GIVEN_FINGERNAILS': 2,
    'MADE_RELIC': 3,
    'GIVEN_RELIC': 4,
    'GIVEN_RIDDLE': 5,
    'SOLVED_RIDDLE': 6,
    'SKAVID_CRYSTAL': 7,
    'FED_NIGHTSHADE': 8,
    'LEARNED_POTION': 9,
    'MADE_POTION': 10,
    'FOUND_ALL_CRYSTALS': 11,
    'COMPLETE': 13,
    'READ_SCROLL': 14,
})
WATCHTOWER_QUEST = 'Watch Tower'
FLAG_LINES = [
    ["i returned og's stolen gold", 'helped-og'],
    ['og wants me to', 'spoken-og'],
    ["i have og's", 'spoken-og'],
    ["i knocked out one of gorad's teeth", 'helped-grew'],
    ['grew wants me to', 'spoken-grew'],
    ["i have one of gorad's teeth", 'spoken-grew'],
    ['i gave the bones to toban', 'helped-toban'],
    ['toban wants the', 'spoken-toban'],
    ['i have the dragon bones', 'spoken-toban'],
    ['the north west guard wants', 'looking-relic'],
    ['the north-east guard wants', 'market-asked'],
    ['i gave the north-east guard a rock cake', 'market-paid'],
    ['i have it with me now, so i can navigate', 'has-map'],
    ['i have been taught a few words', 'learning-skavid'],
    ["'cur bidith' - 'ig'", 'learned-ig'],
    ["'gor cur' - 'ar'", 'learned-ar'],
    ["'bidith tanath' - 'cur'", 'learned-cur'],
    ["'gor nod' - 'nod'", 'learned-nod'],
    ['i have mined the sacred rock', 'mined-rock'],
]
# The journal drops a tribe's "wants" line once that tribe is satisfied, so the helped-* line is the only evidence left that we spoke to them.
IMPLIED = [['helped-og', 'spoken-og'], ['helped-grew', 'spoken-grew'], ['helped-toban', 'spoken-toban']]


def shamans_to_kill(text):
    """The N in "kill N ogre shaman", or None."""
    at = text.find(' ogre shaman')
    while at >= 0:
        start = at
        while start > 0 and text[start - 1] in '0123456789':
            start -= 1
        if start < at and text[:start].endswith('kill '):
            return text[start:at]
        at = text.find(' ogre shaman', at + 1)
    return None


def read_flags(text):
    flags = set()
    for needle, flag in FLAG_LINES:
        if (needle in text):
            flags.add(flag)
    for source, implied in IMPLIED:
        if (source in flags):
            flags.add(implied)
    kills = shamans_to_kill(text)
    if kills is not None:
        flags.add('shamans-left:' + kills)
    elif ('i killed all the ogre shamans' in text):
        flags.add('shamans-left:0')
    return flags


def read_stage(text):
    # Later entries retain the complete earlier history, so match newest first.
    if ('quest complete!' in text):
        return WATCHTOWER_STAGE.COMPLETE
    if ('i have taken the crystals to the watchtower wizard' in text):
        return WATCHTOWER_STAGE.FOUND_ALL_CRYSTALS
    if ('he infused it into a magic ogre potion' in text):
        return WATCHTOWER_STAGE.MADE_POTION
    # Needles avoid punctuation next to a colour tag: stripping "@dbl@" leaves a space before the mark, so "potion." normalises to "potion .".
    if ('i need to get it enchanted' in text) or ('i need to make the' in text):
        return WATCHTOWER_STAGE.LEARNED_POTION
    if ('i need to defeat the ogre shamans and find the other' in text):
        return WATCHTOWER_STAGE.FED_NIGHTSHADE
    if ("the other crystals are in the shamans' enclave" in text):
        return WATCHTOWER_STAGE.SKAVID_CRYSTAL
    if ('i was given a map by the guard' in text):
        return WATCHTOWER_STAGE.SOLVED_RIDDLE
    if ('some guards gave me a puzzle' in text):
        return WATCHTOWER_STAGE.GIVEN_RIDDLE
    if ('i gave the ogre relic to the north west guard' in text):
        return WATCHTOWER_STAGE.GIVEN_RELIC
    if ('now i need to deal with the tribal ogres' in text):
        return WATCHTOWER_STAGE.GIVEN_FINGERNAILS
    if ('i accepted the challenge of finding the lost' in text):
        return WATCHTOWER_STAGE.STARTED
    if ('i can start this quest' in text):
        return WATCHTOWER_STAGE.NOT_STARTED
    return None


def parse_watchtower_journal(lines):
    text = normalize(lines)
    stage = read_stage(text)
    return (None if stage is None else QuestProgress(stage, read_flags(text)))


def read_watchtower_progress():
    status = quests.status(WATCHTOWER_QUEST)
    if status == 'complete':
        return QuestProgress(WATCHTOWER_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(WATCHTOWER_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(WATCHTOWER_QUEST)
    progress = parse_watchtower_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress
