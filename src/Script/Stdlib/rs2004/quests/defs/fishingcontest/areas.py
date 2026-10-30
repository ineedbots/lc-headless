"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fishingcontest/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['FC_NAME', 'FC_ID', 'FC_LOC', 'RED_VINE_LOCS', 'FC_NPC', 'FC_TILE', 'HARRY_SHOP', 'DWARF_START', 'DWARF_REPORT', 'BONZO_ENTER', 'BONZO_REPORT', 'in_compound', 'nearest_dwarf', 'nearest_spade']

FC_NAME = 'Fishing Contest'
FC_ID = Record({
    'RED_VINE_WORM': 25,
    'TROPHY': 26,
    'PASS': 27,
    'FISHING_ROD': 307,
    'RAW_SARDINE': 327,
    'RAW_GIANT_CARP': 338,
    'SPADE': 952,
    'COINS': 995,
    'GARLIC': 1550,
})
FC_LOC = Record({'WALL_PIPE': 41, 'GATE_LEFT': 47, 'GATE_RIGHT': 48})
# Why: the patch is drawn from 7 vine shapes that all render "Vine", and other vines elsewhere in the world share the name.
RED_VINE_LOCS = [58, 2989, 2990, 2991, 2992, 2993, 2994]
# Why: all 4 contest spots render "Fishing spot" and stand within 15 tiles of each other, so only the id separates the winning one from the decoys.
FC_NPC = Record({'WILLOW_SPOT': 233, 'PIPES_SPOT': 234})
FC_TILE = Record({
    'GATE_OUTSIDE': Tile(2643, 3442, 0),
    'GATE_INSIDE': Tile(2642, 3442, 0),
    'BONZO': Tile(2640, 3440, 0),
    'PIPE_STAND': Tile(2638, 3446, 0),
    'PIPES_SPOT': Tile(2638, 3444, 0),
    'VINES': Tile(2632, 3497, 0),
    'SPADE_FALADOR': Tile(2981, 3369, 0),
    'SPADE_ARDOUGNE': Tile(2574, 3331, 0),
    'HARRY': Tile(2834, 3445, 0),
    'DWARF_WEST': Tile(2820, 3486, 0),
    'DWARF_EAST': Tile(2876, 3482, 0),
})
HARRY_SHOP = Record({'npc': 'Harry', 'anchor': FC_TILE.HARRY})
# Why: the start chain is 6 choices deep and every page repeats "grumpy little man", so the preference list has to name a rung of its own at each step.
DWARF_START = Record({
    'npc': 'Mountain Dwarf',
    'anchor': FC_TILE.DWARF_WEST,
    'leash': 8,
    'prefer': [
    'I was just wondering what was down those stairs?',
    'Why not?',
    "If you were my friend I wouldn't mind.",
    "Well, let's be friends!",
    'And how am I meant to do that?',
    "Fortunately I'm alright at fishing!",
],
})
_merged1 = {}
for _k, _v in (DWARF_START._fields if isinstance(DWARF_START, Record) else DWARF_START).items():
    _merged1[_k] = _v


for _k, _v in {'prefer': ['I need another competition pass.']}.items():
    _merged1[_k] = _v


DWARF_REPORT = Record(_merged1)
BONZO_ENTER = Record({'npc': 'Bonzo', 'anchor': FC_TILE.BONZO, 'leash': 8, 'prefer': ["I'll enter the competition please."]})
_merged2 = {}
for _k, _v in (BONZO_ENTER._fields if isinstance(BONZO_ENTER, Record) else BONZO_ENTER).items():
    _merged2[_k] = _v


for _k, _v in {'prefer': []}.items():
    _merged2[_k] = _v


BONZO_REPORT = Record(_merged2)


# Why: The gate is the only edge into the 184-tile enclosure, so position alone identifies the side.
def in_compound(t):
    """Inside the Hemenster competition ground."""
    return not not t and t.level == 0 and t.x >= 2628 and t.x <= 2642 and t.z >= 3413 and t.z <= 3446


def nearest_dwarf(t):
    """Whichever tunnel mouth is nearer; both dwarves run the same script."""
    if not t:
        return FC_TILE.DWARF_EAST
    return (FC_TILE.DWARF_WEST if FC_TILE.DWARF_WEST.distance_to(t) <= FC_TILE.DWARF_EAST.distance_to(t) else FC_TILE.DWARF_EAST)


RIDGE_X = 2860


# Why: straight-line distance picks Falador from Catherby, 146 tiles against Edmond's 261, and then walks 363 of path over the mountain and its aggressive wolves, where Ardougne is 312 on the flat.
def nearest_spade(t):
    """The spade spawn on this side of the mountain."""
    return (FC_TILE.SPADE_ARDOUGNE if t and t.x < RIDGE_X else FC_TILE.SPADE_FALADOR)
