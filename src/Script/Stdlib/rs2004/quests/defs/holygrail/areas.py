"""Ported from rs2b0t's src/bot/api/ai/quests/defs/holygrail/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['GRAIL_NAME', 'ITEM', 'MERLIN_ID', 'TITAN_ID', 'WHISTLE_DOOR_ID', 'GRAIL_TILE', 'KING_ARTHUR_START', 'KING_ARTHUR_FINISH', 'MERLIN', 'HIGH_PRIEST', 'GALAHAD', 'FISHERMAN', 'FISHER_KING', 'SIR_PERCIVAL', 'LADY_OF_THE_LAKE', 'in_blighted_realm', 'in_renewed_realm', 'in_fisher_realm', 'east_of_titan', 'in_castle_upstairs']

GRAIL_NAME = 'Holy Grail'
# Why: every one of these names is unique in the object table, so no ids are needed.
ITEM = Record({
    'NAPKIN': 'Holy table napkin',
    'WHISTLE': 'Magic whistle',
    'BELL': 'Grail bell',
    'GRAIL': 'Holy grail',
    'EXCALIBUR': 'Excalibur',
    'COINS': 'Coins',
})
MERLIN_ID = 213
TITAN_ID = 221
WHISTLE_DOOR_ID = 22
GRAIL_TILE = Record({
    'MERLIN_WORKSHOP': Tile(2767, 3500, 1),
    'DRAYNOR_BANK': Tile(3093, 3243, 0),
    'WHISTLE_STAND': Tile(3106, 3359, 2),
    'SIX_HEADS': Tile(2741, 3235, 0),
    'REALM_ARRIVAL': Tile(2806, 4715, 0),
    'TITAN_STAND': Tile(2792, 4722, 0),
    'TITAN_WEST': Tile(2790, 4722, 0),
    'BELL_SPAWN': Tile(2762, 4694, 0),
    'RING_STAND': Tile(2763, 4693, 0),
    'CASTLE_LANDING': Tile(2761, 4692, 0),
    'CASTLE_STAIR': Tile(2760, 4680, 0),
    'FISHER_KING_DOOR': Tile(2767, 4688, 1),
    'FISHER_KING': Tile(2762, 4688, 1),
    'GOBLIN_SACKS': Tile(2960, 3507, 0),
    'SACKS_STAND': Tile(2961, 3507, 0),
    'RENEWED_ARRIVAL': Tile(2678, 4715, 0),
    'GRAIL_STAND': Tile(2649, 4683, 2),
    'GRAIL_TABLE': Tile(2649, 4684, 2),
})
KING_ARTHUR_START = NpcStop('King Arthur', Tile(2764, 3515, 0), 8, ['Now I am a knight of the round table', 'Tell me of this quest.', "I'd enjoy trying that."])
KING_ARTHUR_FINISH = NpcStop('King Arthur', Tile(2764, 3515, 0), 8, [])
MERLIN = NpcStop('Merlin', GRAIL_TILE.MERLIN_WORKSHOP, 6, ['Thank you for the advice.'])
HIGH_PRIEST = NpcStop('High Priest', Tile(2851, 3349, 0), 8, ['Ok, I will go searching.'])
GALAHAD = NpcStop('Galahad', Tile(2612, 3474, 0), 8, [
    'I seek an item from the realm of the Fisher King.',
    'I have lost the holy table napkin',
    "Well, I'd better be going then.",
    'Do you get lonely out here on your own?',
])
FISHERMAN = NpcStop('Fisherman', Tile(2802, 4706, 0), 8, ['Any idea how to get into the castle?'])
FISHER_KING = NpcStop('The Fisher King', GRAIL_TILE.FISHER_KING, 10, ["You don't look too well."])
SIR_PERCIVAL = NpcStop('Sir Percival', GRAIL_TILE.SACKS_STAND, 8, ['Your father wishes to speak to you.', 'Come with me, I shall make you a king.'])
LADY_OF_THE_LAKE = NpcStop('The Lady of the Lake', Tile(2924, 3405, 0), 6, ['I seek the sword Excalibur.'])


def within(t, x0, x1, z0, z1):
    return not not t and t.x >= x0 and t.x <= x1 and t.z >= z0 and t.z <= z1


def in_blighted_realm(t):
    """The blighted Realm of the Fisher King, mapsquare 43x73, every level."""
    return within(t, 2752, 2815, 4672, 4735)


def in_renewed_realm(t):
    """The renewed realm the whistle lands in once Percival has been sent home."""
    return within(t, 2624, 2687, 4672, 4735)


def in_fisher_realm(t):
    return in_blighted_realm(t) or in_renewed_realm(t)


# Why: the barricades and the blocked column at x 2791 split the blighted realm in 2 with the titan's tile as the only join, so which side we're on says whether the fight is still owed.
# Why: the pocket's west edge steps east as z falls, so no rectangle fits; these bands sit in the gap between the 2 components on every row.
def east_of_titan(t):
    """True on the whistle's landing side of the titan, where the crossing is still unpaid."""
    if not t or t.level != 0 or not in_blighted_realm(t) or t.z < 4709:
        return False
    if t.z >= 4728:
        return t.x >= 2786
    if t.z >= 4713:
        return t.x >= 2791
    if t.z >= 4712:
        return t.x >= 2794
    if t.z >= 4711:
        return t.x >= 2795
    if t.z >= 4710:
        return t.x >= 2797
    return t.x >= 2800


# Why: the castle floor plan interleaves with the ground outside, so no rectangle separates them, but only the castle has an upper floor.
def in_castle_upstairs(t):
    """True on a Grail castle floor above the ground, which only the bell reaches."""
    return in_blighted_realm(t) and t.level >= 1
