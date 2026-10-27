"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dragonslayer/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.game import reader
from rs2004.tabs import quests

__all__ = ['DRAGON_STAGE', 'parse_dragon_journal', 'journal_read', 'describe_journal', 'read_dragon_progress']

import _core
DRAGON_STAGE = Record({
    'NOT_STARTED': 0,
    'SPOKEN_GUILDMASTER': 1,
    'SPOKEN_OZIACH': 2,
    'BOUGHT_SHIP': 3,
    'REPAIRED_SHIP': 7,
    'NED_GIVEN_MAP': 8,
    'SAILED_TO_CRANDOR': 9,
    'COMPLETE': 10,
})
DRAGON_QUEST = 'Dragon Slayer'
FLAG_LINES = [
    ['i should return to oziach for more detailed instructions', 'needs-briefing'],
    ["hidden in melzar's maze", 'map-melzar'],
    ['hidden in beneath ice', 'map-ice'],
    ['the goblin, wormbrain, stole', 'map-wormbrain'],
    ['gave me an anti-dragonbreath', 'has-shield'],
    ["the map's behind a door below", 'asked-oracle'],
    ['i have repaired my ship using wooden planks', 'ship-repaired'],
    ['has agreed to sail', 'ned-hired'],
    ['i have found the secret passage', 'secret-passage'],
]


def read_flags(text):
    flags = set()
    for needle, flag in FLAG_LINES:
        if (needle in text):
            flags.add(flag)
    return flags


def read_stage(text):
    # Each entry keeps the earlier history, so match the newest marker first.
    if ('quest complete!' in text):
        return DRAGON_STAGE.COMPLETE
    if ('all i need to do is kill the' in text):
        return DRAGON_STAGE.SAILED_TO_CRANDOR
    if ('set sail for' in text):
        return DRAGON_STAGE.NED_GIVEN_MAP
    if ('i still need to find a captain' in text):
        return (DRAGON_STAGE.REPAIRED_SHIP if ('i have repaired my ship using wooden planks' in text) else DRAGON_STAGE.BOUGHT_SHIP)
    if ('i should see if there is a ship for sale' in text):
        return DRAGON_STAGE.SPOKEN_OZIACH
    if ('i should return to oziach for more detailed instructions' in text):
        return DRAGON_STAGE.SPOKEN_OZIACH
    if ('i should speak to oziach' in text):
        return DRAGON_STAGE.SPOKEN_GUILDMASTER
    if ('i can start this quest' in text):
        return DRAGON_STAGE.NOT_STARTED
    return None


def parse_dragon_journal(lines):
    text = normalize(lines)
    stage = read_stage(text)
    return (None if stage is None else Record({'stage': stage, 'flags': read_flags(text)}))


# Why: the journal modal doesn't always open (leftover dialogue, level change, unrefreshed tab), so the last good read stands in until the next success.
last_good = None
# Why: `decide()` branches on this, so a flag that flaps between loops means the read is failing.
journal_read = Record({'reads': 0, 'failures': 0, 'cached': False, 'chars': 0, 'flags': []})


def describe_journal():
    stage = journal_read.stage
    flags = journal_read.flags
    cached = journal_read.cached
    failures = journal_read.failures
    reads = journal_read.reads
    return f"stage={(stage if stage is not None else '?')} flags=[{','.join(flags) or 'none'}]" + f"{(' (CACHED — this read failed)' if cached else '')}" + f"{(f' reads={reads} failures={failures}' if failures > 0 else '')}"


def read_dragon_progress():
    global last_good
    status = quests.status(DRAGON_QUEST)
    if status == 'complete':
        return Record({'stage': DRAGON_STAGE.COMPLETE, 'flags': set()})
    if status == 'not_started':
        return Record({'stage': DRAGON_STAGE.NOT_STARTED, 'flags': set()})
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(DRAGON_QUEST)
    progress = parse_dragon_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    journal_read.reads += 1
    journal_read.chars = len(normalize(lines))
    journal_read.cached = progress is None
    if progress:
        last_good = progress
    else:
        journal_read.failures += 1
    used = (progress if progress is not None else last_good)
    journal_read.stage = (used.stage if used is not None else None)
    _v1 = (used.flags if used is not None else None)
    journal_read.flags = list(((_v1 if _v1 is not None else [])))
    return used
