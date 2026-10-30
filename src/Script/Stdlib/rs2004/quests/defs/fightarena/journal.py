"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fightarena/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.journal_text import normalize_journal
from rs2004.tabs import quests
import _core

__all__ = ['FIGHT_ARENA_QUEST', 'FA_STAGE', 'parse_fight_arena_journal', 'reset_fight_arena_stage', 'read_fight_arena_stage']

FIGHT_ARENA_QUEST = 'Fight Arena'
FA_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'OBTAINED_ARMOUR': 2,
    'SPOKEN_DRUNKGUARD': 3,
    'GIVEN_KHALI_BREW': 5,
    'ENTERED_OGRE_FIGHT': 6,
    'DEFEATED_OGRE': 8,
    'SENT_JAIL': 9,
    'DEFEATED_SCORPION': 10,
    'DEFEATED_BOUNCER': 11,
    'FREED_SERVILS': 12,
    'DEFEATED_KHAZARD': 13,
    'COMPLETE': 14,
})
# Why: the journal keeps every earlier paragraph, so the newest line present is the stage and the order of this table is the parse.
# Why: no needle may end on punctuation, as a colour tag beside a mark normalises to a space between them.
NEEDLES = [
    ['quest complete!', FA_STAGE.COMPLETE],
    ['i eventually killed', FA_STAGE.DEFEATED_KHAZARD],
    ['challenged me to fight him, but i ran away', FA_STAGE.FREED_SERVILS],
    ['wants to kill me himself', FA_STAGE.DEFEATED_BOUNCER],
    ['ordered me to fight his pet', FA_STAGE.DEFEATED_SCORPION],
    ['going to have to fight in the arena', FA_STAGE.SENT_JAIL],
    ['should talk to jeremy in the fight arena', FA_STAGE.DEFEATED_OGRE],
    ['i need to protect jeremy and his father', FA_STAGE.ENTERED_OGRE_FIGHT],
    ["now i've got the keys", FA_STAGE.GIVEN_KHALI_BREW],
    ['guards told me that he really likes', FA_STAGE.SPOKEN_DRUNKGUARD],
    ['luckily i found some khazard armour in a chest', FA_STAGE.OBTAINED_ARMOUR],
    ['and try to find her family', FA_STAGE.STARTED],
    ['i can start this quest by speaking to', FA_STAGE.NOT_STARTED],
]


def parse_fight_arena_journal(lines):
    text = normalize_journal(lines)
    if len(text) == 0:
        return None
    hit = ([entry for entry in NEEDLES if entry[0] in text] or [None])[0]
    return hit[1] if hit is not None else None


# Why: a read taken while something is swinging comes back empty, and standing still to re-read it is the one thing the arena punishes.
# Why: the stage only ever moves forward, so the last one read is a sound floor to act on until the next read lands.
last_read = None


def reset_fight_arena_stage():
    """Forget the cached stage. Tests and a fresh account want a clean slate."""
    global last_read
    last_read = None


# Why: the journal body is built only when the player opens the quest, and it is a main modal that hides every later read until it is closed.
def read_fight_arena_stage():
    """The stage, read from the quest list colour and the journal scroll."""
    global last_read
    status = quests.status(FIGHT_ARENA_QUEST)
    if status == 'complete':
        last_read = FA_STAGE.COMPLETE
        return FA_STAGE.COMPLETE
    if status == 'not_started':
        last_read = FA_STAGE.NOT_STARTED
        return FA_STAGE.NOT_STARTED
    if status != 'in_progress':
        return last_read
    _w2 = yield from quests.journal(FIGHT_ARENA_QUEST)
    stage = parse_fight_arena_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if stage is not None:
        last_read = stage
        return stage
    return last_read
