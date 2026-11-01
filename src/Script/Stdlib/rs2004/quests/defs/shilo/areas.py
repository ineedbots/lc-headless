"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['SV_ITEM', 'SV_LOC', 'SV_NPC', 'SV_TILE', 'in_dolmen_room', 'BONE_SPAWNS', 'shilo_area']

# Why: these are the engine's names, some misspelled in the configs ("Rashiliya corpse", "Stone-plaque"), and the 5 Jungle Potion unids all render "Unidentified herb", so lookups go by id.
SV_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'SPADE': Record({'id': 952, 'name': 'Spade'}),
    'CHISEL': Record({'id': 1755, 'name': 'Chisel'}),
    'HAMMER': Record({'id': 2347, 'name': 'Hammer'}),
    'TINDERBOX': Record({'id': 590, 'name': 'Tinderbox'}),
    'CANDLE': Record({'id': 36, 'name': 'Candle'}),
    'LIT_CANDLE': Record({'id': 33, 'name': 'Lit candle'}),
    'BRONZE_BAR': Record({'id': 2349, 'name': 'Bronze bar'}),
    'BRONZE_WIRE': Record({'id': 1794, 'name': 'Bronze wire'}),
    'BONES': Record({'id': 526, 'name': 'Bones'}),
    'WAMPUM_BELT': Record({'id': 625, 'name': 'Wampum belt'}),
    'TATTERED_SCROLL': Record({'id': 607, 'name': 'Tattered scroll'}),
    'CRUMPLED_SCROLL': Record({'id': 608, 'name': 'Crumpled scroll'}),
    'ZADIMUS_CORPSE': Record({'id': 610, 'name': 'Zadimus corpse'}),
    'BONE_SHARD': Record({'id': 604, 'name': 'Bone shard'}),
    'BONE_KEY': Record({'id': 605, 'name': 'Bone key'}),
    'SWORD_POMMEL': Record({'id': 623, 'name': 'Sword pommel'}),
    'BONE_BEADS': Record({'id': 618, 'name': 'Bone beads'}),
    'DEAD_BEADS': Record({'id': 616, 'name': 'Beads of the dead'}),
    'RASH_CORPSE': Record({'id': 609, 'name': 'Rashiliya corpse'}),
})
SV_LOC = Record({
    'MOUND': 'Mound of earth',
    'FISSURE': 'Fissure',
    'CAVE_IN': 'Cave in',
    'LOOSE_ROCKS': 'Loose rocks',
    'OLD_SACKS': 'Old sacks',
    'GALLOWS': 'Ancient gallows',
    'WATERFALL_ROCKS': 'Waterfall rocks',
    'WELL_STACKED_ROCKS': 'Well stacked rocks',
    'BERVIRIUS_DOLMEN': 'Tomb dolmen',
    'HANDHOLDS': 'Climbing rocks',
    'PALM_TREE': 'Palm tree',
    'CARVED_DOORS': 'Carved doors',
    'HILLSIDE_ENTRANCE': 'Hillside entrance',
    'TOMB_EXIT': 'Tomb exit',
    'ANCIENT_GATE': 'Ancient metal gate',
    'RASH_ROCKS': 'Rocks',
    'TOMB_DOORS': 'Tomb doors',
    'RASH_DOLMEN': 'Tomb dolmen',
})
SV_NPC = Record({
    'MOSOL_REI': 'Mosol Rei',
    'TRUFITUS': 'Trufitus',
    'JIMINUA': 'Jiminua',
    'NAZASTAROOL': 'Nazastarool',
    'RASHILIYIA': 'Rashiliyia',
    'UNDEAD_ONE': 'Undead One',
})
SV_TILE = Record({
    'ARDOUGNE_BANK': Tile(2616, 3332, 0),
    'JIMINUA': Tile(2767, 3122, 0),
    'ANVIL': Tile(2790, 3101, 0),
    'TRUFITUS': Tile(2809, 3086, 0),
    'MOSOL_REI': Tile(2883, 2951, 0),
    'SACRED_GROUND': Tile(2796, 3088, 0),
    'MOUND_STAND': Tile(2921, 2998, 0),
    'CAVE_IN_NORTH': Tile(2887, 9374, 0),
    'CAVE_IN_SOUTH': Tile(2888, 9283, 0),
    'LOOSE_ROCKS': Tile(2886, 9317, 0),
    'OLD_SACKS': Tile(2938, 9285, 0),
    'GALLOWS': Tile(2933, 9325, 0),
    'WATERFALL_ROCKS': Tile(2939, 9349, 0),
    'WELL_STACKED_ROCKS': Tile(2762, 2989, 0),
    'BERVIRIUS_DOLMEN': Tile(2765, 9364, 0),
    'HANDHOLDS': Tile(2764, 9376, 0),
    'PALM_TREES': Tile(2914, 3092, 0),
    'CARVED_DOORS': Tile(2915, 3090, 0),
    'TOMB_EXIT': Tile(2928, 9526, 0),
    'ANCIENT_GATE': Tile(2929, 9517, 0),
    'RASH_ROCKS_BOTTOM': Tile(2928, 9511, 0),
    'TOMB_DOORS': Tile(2892, 9479, 0),
    'TOMB_DOORS_INSIDE': Tile(2892, 9482, 0),
    'RASH_DOLMEN': Tile(2891, 9487, 0),
})


def in_dolmen_room(tile):
    """The dolmen room, behind the skeletal doors. A plain z test won't do: the corridor east of the doors runs up to z=9511 on the southern side."""
    return tile is not None and tile.x >= 2886 and tile.x <= 2898 and tile.z >= 9481 and tile.z <= 9492


BONE_SPAWNS = [
    Tile(2484, 3221, 0),
    Tile(2480, 3219, 0),
    Tile(2476, 3224, 0),
    Tile(2470, 3223, 0),
    Tile(2466, 3226, 0),
    Tile(2470, 3217, 0),
]
RASH_GATE_Z = 9516
RASH_ROCKS_BOTTOM_Z = 9511


# Why: Rashiliyia's tomb has 3 parts, the corridor from the hillside doors, the ledge the gate drops you onto, and the tomb below the rocks; collapsing the ledge into a neighbour makes the gate re-open forever.
def shilo_area(tile):
    """Which Shilo area a tile is in."""
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    if x >= 2880 and x <= 2943 and z >= 9472 and z <= 9535:
        if z >= RASH_GATE_Z:
            return 'rashEntry'
        return ('rashLedge' if z > RASH_ROCKS_BOTTOM_Z else 'rashInner')
    if x >= 2880 and x <= 2943 and z >= 9344 and z <= 9407:
        return 'ahZaRhoonNorth'
    if x >= 2880 and x <= 2943 and z >= 9280 and z <= 9343:
        return 'ahZaRhoonSouth'
    if x >= 2752 and x <= 2815 and z >= 9344 and z <= 9407:
        return 'berviriusTomb'
    if z >= 4000:
        return 'unknown'
    if x >= 2830 and x <= 2880 and z >= 2930 and z <= 2975:
        return 'shiloVillage'
    return 'karamja'
