"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.geometry import Tile

__all__ = ['SOA_NAME', 'SOA_ID', 'SOA_LOC', 'SOA_TILE', 'RELDO', 'BARAEK', 'TRAMP', 'STRAVEN_JOIN', 'STRAVEN_HANDIN', 'KATRINE_JOIN', 'KATRINE_HANDIN', 'CURATOR', 'ROALD', 'HQ_HOP_DOWN', 'HQ_HOP_UP', 'SOA_HOPS', 'in_phoenix_hq', 'in_phoenix_inner', 'in_weapon_store', 'in_store_ground', 'in_black_arm_inner', 'in_black_arm_upper']

SOA_NAME = 'Shield of Arrav'
SOA_ID = Record({
    'BOOK': 757,
    'STORE_KEY': 759,
    'REPORT': 761,
    'SHIELD_PHOENIX': 763,
    'SHIELD_BLACKARM': 765,
    'CROSSBOW': 767,
    'CERTIFICATE': 769,
    'COINS': 995,
})
SOA_LOC = Record({
    'PHOENIX_DOOR': 2397,
    'STORE_DOOR': 2398,
    'BLACKARM_DOOR': 2399,
    'CUPBOARD_SHUT': 2400,
    'CUPBOARD_OPEN': 2401,
    'BOOKCASE': 2402,
    'CHEST_SHUT': 2403,
    'CHEST_OPEN': 2404,
    'STREET_DOOR': 1530,
    'CELLAR_LADDER': 1754,
    'HQ_LADDER': 2405,
    'STORE_LADDER': 1747,
    'STORE_LADDER_TOP': 1746,
    'BLACKARM_STAIRS': 1722,
    'BLACKARM_STAIRS_TOP': 1723,
})
SOA_TILE = Record({
    'BOOKCASE': Tile(3213, 3493, 0),
    'CELLAR_LADDER': Tile(3244, 3384, 0),
    'HQ_LADDER': Tile(3244, 9784, 0),
    'HQ_SURFACE': Tile(3244, 3382, 0),
    'PHOENIX_DOOR': Tile(3247, 9780, 0),
    'PHOENIX_DOOR_INNER': Tile(3247, 9778, 0),
    'CHEST_STAND': Tile(3235, 9762, 0),
    'STORE_DOOR': Tile(3251, 3386, 0),
    'STORE_DOOR_INNER': Tile(3251, 3384, 0),
    'STORE_LADDER': Tile(3252, 3385, 0),
    'STORE_LADDER_TOP': Tile(3251, 3384, 1),
    'CROSSBOW_WEST': Tile(3243, 3383, 1),
    'CROSSBOW_EAST': Tile(3245, 3385, 1),
    'STREET_DOOR': Tile(3190, 3384, 0),
    'BLACKARM_DOOR': Tile(3185, 3387, 0),
    'BLACKARM_DOOR_INNER': Tile(3185, 3389, 0),
    'BLACKARM_STAIRS': Tile(3188, 3388, 0),
    'BLACKARM_STAIRS_TOP': Tile(3187, 3390, 1),
    'CUPBOARD_STAND': Tile(3187, 3385, 1),
    'JONNY': Tile(3223, 3395, 0),
    'RENDEZVOUS': Tile(3253, 3420, 0),
})
RELDO = Record({'npc': 'Reldo', 'anchor': Tile(3209, 3495, 0), 'leash': 8, 'prefer': ["I'm in search of a quest."]})
BARAEK = Record({
    'npc': 'Baraek',
    'anchor': Tile(3218, 3435, 0),
    'leash': 8,
    'prefer': ['Can you tell me where I can find the Phoenix Gang?', 'Okay. Have 20 gold coins.'],
})
TRAMP = Record({
    'npc': 'Tramp',
    'anchor': Tile(3208, 3391, 0),
    'leash': 8,
    'prefer': ['Is there anything down this alleyway?', 'Do you think they would let me join?'],
})
STRAVEN_JOIN = Record({
    'npc': 'Straven',
    'anchor': Tile(3246, 9780, 0),
    'leash': 6,
    'prefer': ['I know who you are!', "I'd like to offer you my services."],
})
STRAVEN_HANDIN = Record({'npc': 'Straven', 'anchor': Tile(3246, 9780, 0), 'leash': 6, 'prefer': []})
KATRINE_JOIN = Record({
    'npc': 'Katrine',
    'anchor': Tile(3186, 3385, 0),
    'leash': 6,
    'prefer': [
    "I've heard you're the Black Arm Gang.",
    "I'd rather not reveal my sources.",
    'I want to become a member of your gang.',
    "Well, you can give me a try can't you?",
    'Ok, no problem.',
],
})
KATRINE_HANDIN = Record({'npc': 'Katrine', 'anchor': Tile(3186, 3385, 0), 'leash': 6, 'prefer': []})
CURATOR = Record({'npc': 'Curator', 'anchor': Tile(3255, 3446, 0), 'leash': 6, 'prefer': []})
ROALD = Record({'npc': 'King Roald', 'anchor': Tile(3222, 3475, 0), 'leash': 8, 'prefer': []})
# Why: `needsHop` compares z against 6400, so a LadderHop only covers a surface-to-underground move; the two upper floors get climbed inside their own legs.
HQ_HOP_DOWN = Record({'stand': SOA_TILE.CELLAR_LADDER, 'loc_name': 'Ladder', 'op': 'Climb-down', 'arrive': SOA_TILE.HQ_LADDER})
HQ_HOP_UP = Record({'stand': SOA_TILE.HQ_LADDER, 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': SOA_TILE.HQ_SURFACE})
SOA_HOPS = [HQ_HOP_DOWN, HQ_HOP_UP]


def within(t, x0, x1, z0, z1, level):
    return not not t and t.level == level and t.x >= x0 and t.x <= x1 and t.z >= z0 and t.z <= z1


def in_phoenix_hq(t):
    """The hideout is an underground band nothing walks into; the cellar ladder is the only way in or out."""
    return within(t, 3225, 3260, 9750, 9795, 0)


# Why: a flood over the pack puts the chest side at z 9761..9779 and the ladder side at 9780 up, so the split is clean.
def in_phoenix_inner(t):
    """The chest half of the hideout, past the gang door."""
    return within(t, 3233, 3254, 9761, 9779, 0)


def in_weapon_store(t):
    return within(t, 3240, 3256, 3378, 3392, 1)


# Why: a flood over the pack puts this pocket at 10 tiles, and `phoenixdoor2` is its only way in or out.
def in_store_ground(t):
    """The weapon store's ground floor, which the store door seals."""
    return within(t, 3250, 3252, 3382, 3385, 0)


def in_black_arm_inner(t):
    """The stairs half of the Black Arm hideout, past the gang door. Katrine's room is z 3387 and below."""
    return within(t, 3182, 3189, 3388, 3398, 0)


def in_black_arm_upper(t):
    return within(t, 3180, 3196, 3380, 3394, 1)
