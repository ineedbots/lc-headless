"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['NS_QUEST', 'NS_STAGE', 'BLOOM_MAX_COST', 'NS_ID', 'NS_NAME', 'NS_LOC', 'NS_TILE', 'NS_HOPS', 'DREZEL', 'URHNEY', 'FILLIMAN', 'NATURE_SPIRIT', 'DOMMIK', 'BOB', 'in_swamp', 'in_camp', 'in_grotto']

NS_QUEST = 'Nature Spirit'
NS_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 5,
    'ENTERED_SWAMP': 10,
    'FAILED_TALK': 15,
    'SPOKEN_FILLIMAN': 20,
    'SHOWN_MIRROR': 25,
    'GIVEN_JOURNAL': 30,
    'RECEIVED_SPELL': 35,
    'BLESSED': 40,
    'CASTED_SPELL': 45,
    'PICKED_FUNGI': 50,
    'SPOKEN_FILLIMAN2': 55,
    'PERFORMED_RITUAL': 60,
    'ENTERED_GROTTO': 65,
    'FULL_TRANSFORM': 70,
    'BLESSED_SICKLE': 75,
    'CASTED_SICKLE_BLOOM': 80,
    'PICKED_SICKLE': 85,
    'ADDED_POUCH': 90,
    'KILLED_GHAST1': 95,
    'KILLED_GHAST2': 100,
    'KILLED_GHAST3': 105,
    'COMPLETE': 110,
})
# Why: `opheld3,silver_sickle_blessed` charges `random_range(1, 7)` and refuses at 0, so a bar under 7 can still lose the cast.
BLOOM_MAX_COST = 7
NS_ID = Record({
    'GHOSTSPEAK': 552,
    'POUCH_EMPTY': 2957,
    'POUCH': 2958,
    'SICKLE': 2961,
    'SICKLE_BLESSED': 2963,
    'BOWL': 2964,
    'MIRROR': 2966,
    'JOURNAL': 2967,
    'SPELL': 2968,
    'SPELL_USED': 2969,
    'FUNGI': 2970,
    'STEM': 2972,
    'PEAR': 2974,
    'MOULD': 2976,
    'SILVER_ORE': 442,
    'SILVER_BAR': 2355,
    'COINS': 995,
})
NS_NAME = Record({
    'GHOSTSPEAK': 'Ghostspeak amulet',
    'POUCH': 'Druid pouch',
    'SICKLE': 'Silver sickle',
    'SICKLE_BLESSED': 'Silver sickle(b)',
    'BOWL': 'Washing bowl',
    'MIRROR': 'Mirror',
    'JOURNAL': 'Journal',
    'SPELL': 'Druidic spell',
    'SPELL_USED': 'A used spell',
    'FUNGI': 'Mort myre fungi',
    'STEM': 'Mort myre stem',
    'PEAR': 'Mort myre pear',
    'MOULD': 'Sickle mould',
    'SILVER_ORE': 'Silver ore',
    'SILVER_BAR': 'Silver bar',
    'COINS': 'Coins',
})
NS_LOC = Record({
    'LOG': 'Rotting log',
    'FUNGI_LOG': 'Fungi on log',
    'BRANCH': 'Rotting branch',
    'BUDDING_BRANCH': 'Budding branch',
    'BUSH': 'A small bush',
    'PEAR_BUSH': 'A golden pear bush',
    'GROTTO_DOOR': 'Grotto',
    'GROTTO_TREE': 'Grotto tree',
    'GROTTO_POOL': 'Grotto',
    'ALTAR': 'Altar of nature',
    'TEMPLE_ALTAR': 'Altar',
    'STONE': 'Stone',
    'FURNACE': 'Furnace',
})
NS_TILE = Record({
    'DREZEL': Tile(3439, 9895, 0),
    'GATE': Tile(3443, 3461, 0),
    'CAMP': Tile(3440, 3337, 0),
    'SPIRIT': Tile(3440, 3336, 0),
    'NATURE_STONE': Tile(3439, 3336, 0),
    'FAITH_STONE': Tile(3440, 3335, 0),
    'SPIRIT_STONE': Tile(3441, 3336, 0),
    'BOWL': Tile(3437, 3337, 0),
    'GROTTO_TREE': Tile(3439, 3338, 0),
    'GROTTO_DOOR': Tile(3440, 3337, 0),
    'GROTTO_INSIDE': Tile(3442, 9734, 0),
    'POUCH': Tile(3443, 9741, 0),
    'TEMPLE_ALTAR': Tile(3416, 3488, 0),
    'GHAST_HUNT': Tile(3424, 3337, 0),
    'URHNEY': Tile(3235, 3154, 0),
    'DOMMIK': Tile(3322, 3194, 0),
    'BOB': Tile(3232, 3203, 0),
    'FURNACE': Tile(3272, 3183, 0),
    'SILVER_ROCKS': Tile(3294, 3301, 0),
    'VARROCK_EAST_BANK': Tile(3253, 3420, 0),
    'ALKHARID_BANK': Tile(3269, 3167, 0),
})
NS_HOPS = [
    Record({
    'stand': Tile(3405, 3506, 0),
    'loc_name': 'Trapdoor',
    'op': 'Climb-down',
    'open': 'Open',
    'arrive': Tile(3405, 9907, 0),
}),
    Record({'stand': Tile(3405, 9907, 0), 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': Tile(3405, 3507, 0)}),
]
DREZEL = Record({
    'npc': 'Drezel',
    'anchor': NS_TILE.DREZEL,
    'leash': 4,
    'prefer': [
    'Is there anything else interesting to do around here?',
    'Well, what is it, I may be able to help?',
    "Yes, I'll go and look for him.",
    "Yes, I'm sure.",
],
})
URHNEY = Record({
    'npc': 'Father Urhney',
    'anchor': NS_TILE.URHNEY,
    'leash': 6,
    'prefer': ['Father Aereck sent me to talk to you.', "He's got a ghost haunting his graveyard.", "I've lost the amulet."],
})
FILLIMAN = Record({
    'npc': 'Filliman Tarlock',
    'anchor': NS_TILE.SPIRIT,
    'leash': 4,
    'prefer': ["I'm wearing an amulet of ghost speak!", 'Ok, thanks.'],
})
NATURE_SPIRIT = Record({'npc': 'Nature Spirit', 'anchor': NS_TILE.GROTTO_INSIDE, 'leash': 8, 'prefer': ['Ok thanks.']})
DOMMIK = Record({'npc': 'Dommik', 'anchor': NS_TILE.DOMMIK})
BOB = Record({'npc': 'Bob', 'anchor': NS_TILE.BOB})


def in_swamp(t):
    """The `inzone` the bloom spell and the decay timer both test."""
    return not not t and t.level == 0 and t.x >= 3392 and t.x <= 3519 and t.z >= 3328 and t.z <= 3455


def in_camp(t):
    """The pocket the swamp cannot decay you in."""
    return not not t and t.level == 0 and t.x >= 3434 and t.x <= 3448 and t.z >= 3330 and t.z <= 3344


# Why: the grotto is entered and left by scripted teleports alone, and it moves up a level once the quest completes.
def in_grotto(t):
    """The sealed pocket under the camp."""
    return not not t and t.x >= 3430 and t.x <= 3455 and t.z >= 9720 and t.z <= 9750
