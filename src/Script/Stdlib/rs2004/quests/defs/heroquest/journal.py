"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.heroquest.areas import HERO_NAME
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal
from rs2004.tabs import quests

__all__ = ['HERO_STAGE', 'parse_hero_quest_journal', 'reset_hero_quest_progress', 'read_hero_quest_progress']

HERO_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'PHOENIX_SPOKEN': 2,
    'PHOENIX_ALFONSE': 3,
    'PHOENIX_CHARLIE': 4,
    'PHOENIX_KILLED_GRIP': 5,
    'PHOENIX_ARMBAND': 6,
    'BLACKARM_SPOKEN': 7,
    'BLACKARM_HQ': 8,
    'BLACKARM_PAPERS': 9,
    'BLACKARM_MANSION': 10,
    'BLACKARM_PAPERS_GIVEN': 11,
    'BLACKARM_LOOTED': 12,
    'BLACKARM_ARMBAND': 13,
    'COMPLETE': 14,
})


# Why: colour tags become a space, so no needle may span a tag boundary, and every needle below opens with one because "she gave me" contains "he gave me".
def normalize(lines):
    body = normalize_journal(lines)
    return ('' if len(body) == 0 else f' {body} ')


# Why: the page keeps every earlier line struck through, so this order separates the stages: each needle is that stage's own next-step line, which no later page repeats.
STAGES = [
    [' quest complete!', HERO_STAGE.COMPLETE],
    [' in reward she gave me a master thief', HERO_STAGE.BLACKARM_ARMBAND],
    [' to prove my skills', HERO_STAGE.PHOENIX_ARMBAND],
    [' after rewarding the player who assisted me', HERO_STAGE.BLACKARM_LOOTED],
    [' i can move around the hideout', HERO_STAGE.BLACKARM_PAPERS_GIVEN],
    [' need to present myself to', HERO_STAGE.BLACKARM_MANSION],
    [' disguise myself as', HERO_STAGE.BLACKARM_PAPERS],
    [' speak to other gang members', HERO_STAGE.BLACKARM_HQ],
    [' say the password she gave me', HERO_STAGE.BLACKARM_SPOKEN],
    [' as soon as they have given me my', HERO_STAGE.PHOENIX_KILLED_GRIP],
    [' help me get through this door', HERO_STAGE.PHOENIX_CHARLIE],
    [' speak to charlie round the back', HERO_STAGE.PHOENIX_ALFONSE],
    [' use the password he gave me at', HERO_STAGE.PHOENIX_SPOKEN],
    [' i should visit their hideout', HERO_STAGE.STARTED],
    [' leader of the black arm gang', HERO_STAGE.STARTED],
    [' i can start this quest by speaking to', HERO_STAGE.NOT_STARTED],
    [' will let me into the', HERO_STAGE.STARTED],
]
# Why: the 3 item lines are driven by `~obj_gettotal`, which counts the bank as well as the pack, so they say the item exists somewhere, never that it's carried.
FLAGS = [
    [' firebird feather - i now have one', 'feather'],
    [' cooked lava eel - i now have one', 'eel'],
    [' armband - i now have one', 'armband'],
    [' i have all required items', 'ready-to-hand-in'],
]


def parse_hero_quest_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    hit = ([(needle, _2) for needle, _2 in STAGES if (needle in text)] or [None])[0]
    if not hit:
        return None
    flags = set()
    for needle, flag in FLAGS:
        if (needle in text):
            flags.add(flag)
    return QuestProgress(hit[1], flags)


last_good = None


def reset_hero_quest_progress():
    """Test seam: the last good read is memoised for the process."""
    global last_good
    last_good = None


def read_hero_quest_progress():
    global last_good
    status = quests.status(HERO_NAME)
    if status == 'complete':
        return QuestProgress(HERO_STAGE.COMPLETE)
    if status == 'not_started':
        return QuestProgress(HERO_STAGE.NOT_STARTED)
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(HERO_NAME)
    progress = parse_hero_quest_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)
