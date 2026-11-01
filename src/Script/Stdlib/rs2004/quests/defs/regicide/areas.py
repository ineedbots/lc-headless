"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['RG_ITEM', 'RG_MIXES', 'RG_NPC', 'RG_LOC', 'RG_SULPHUR_LOCS', 'RG_LIMESTONE_LOCS', 'RG_TILE', 'regicide_area', 'held', 'banked', 'worn', 'carried', 'owned', 'count_held']

# Why: "Barrel bomb" is the display name of both the sealed barrel and the fused one, and "Naphtha mix" of both half-mixes, so every lookup here goes through the id.
RG_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'SHARK': Record({'id': 385, 'name': 'Shark'}),
    'COAL': Record({'id': 453, 'name': 'Coal'}),
    'PICKAXE': Record({'id': 1265, 'name': 'Bronze pickaxe'}),
    'PESTLE': Record({'id': 233, 'name': 'Pestle and mortar'}),
    'POT': Record({'id': 1931, 'name': 'Pot'}),
    'BALL_OF_WOOL': Record({'id': 1759, 'name': 'Ball of wool'}),
    'TINDERBOX': Record({'id': 590, 'name': 'Tinderbox'}),
    'SPADE': Record({'id': 952, 'name': 'Spade'}),
    'SHORTBOW': Record({'id': 841, 'name': 'Shortbow'}),
    'BRONZE_ARROW': Record({'id': 882, 'name': 'Bronze arrow'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'LOGS': Record({'id': 1511, 'name': 'Logs'}),
    'RAW_RABBIT': Record({'id': 3226, 'name': 'Raw rabbit'}),
    'COOKED_RABBIT': Record({'id': 3228, 'name': 'Cooked rabbit'}),
    'SUMMONS': Record({'id': 3206, 'name': "King's message"}),
    'MESSAGE': Record({'id': 3207, 'name': 'Iorwerths message'}),
    'PENDANT': Record({'id': 3208, 'name': 'Crystal pendant'}),
    'SULPHUR': Record({'id': 3209, 'name': 'Sulphur'}),
    'LIMESTONE': Record({'id': 3211, 'name': 'Limestone'}),
    'QUICKLIME': Record({'id': 3213, 'name': 'Quicklime'}),
    'QUICKLIME_DUST': Record({'id': 3214, 'name': 'Pot of quicklime'}),
    'SULPHUR_DUST': Record({'id': 3215, 'name': 'Ground sulphur'}),
    'BARREL': Record({'id': 3216, 'name': 'Barrel'}),
    'BARREL_LID': Record({'id': 3218, 'name': 'Barrel bomb'}),
    'BARREL_FUSED': Record({'id': 3219, 'name': 'Barrel bomb'}),
    'BARREL_TAR': Record({'id': 3220, 'name': 'Barrel of coal-tar'}),
    'BARREL_NAPHTHA': Record({'id': 3221, 'name': 'Barrel of naphtha'}),
    'MIX_SULPHUR': Record({'id': 3222, 'name': 'Naphtha mix'}),
    'MIX_QUICKLIME': Record({'id': 3223, 'name': 'Naphtha mix'}),
    'CLOTH': Record({'id': 3224, 'name': 'Cloth'}),
    'BOOK': Record({'id': 3230, 'name': 'Big book of bangs'}),
})
RG_MIXES = [RG_ITEM.MIX_QUICKLIME, RG_ITEM.MIX_SULPHUR]
RG_NPC = Record({
    'MESSENGER': 1210,
    'IORWERTH': 1182,
    'TRACKER': 1199,
    'OLD_CAMP_GUARD': 1200,
    'CAMP_GUARD': 1203,
    'LAZY_GUARD': 1205,
    'ARIANWYN': 1202,
    'RABBIT': 1192,
    'QUARTERMASTER': 1208,
})
RG_LOC = Record({
    'WELL_OF_VOYAGE': 4004,
    'WELL_BACK': 4005,
    'TEMPLE_ENTRANCE': 4006,
    'TEMPLE_EXIT': 4007,
    'FOOTPRINTS': 3941,
    'LOOM': 787,
    'FURNACE': 3994,
    'TAR': 3975,
    'SULPHUR1': 3962,
    'SULPHUR2': 3963,
    'SULPHUR3': 3964,
    'STILL': 4026,
    'CATAPULT': 3976,
    'FURNACE_MAIN': 2781,
    'FURNACE_SIDE': 2785,
    'LIMESTONE1': 4029,
    'LIMESTONE2': 4028,
    'LIMESTONE3': 4027,
    'GATE_LEFT': 3945,
    'GATE_RIGHT': 3944,
})
RG_SULPHUR_LOCS = [RG_LOC.SULPHUR1, RG_LOC.SULPHUR2, RG_LOC.SULPHUR3]
RG_LIMESTONE_LOCS = [RG_LOC.LIMESTONE1, RG_LOC.LIMESTONE2, RG_LOC.LIMESTONE3]
# Why: Use every footprint tile as a stand because pathing to a multi-tile loc origin can fail.
RG_TILE = Record({
    'ARDOUGNE_BANK': Tile(2655, 3283, 0),
    'ARDOUGNE_RANGE': Tile(2648, 3298, 0),
    'ARDOUGNE_FURNACE': Tile(2601, 3309, 0),
    'LATHAS': Tile(2578, 3293, 1),
    'IBAN_DOOR': Tile(2145, 4647, 1),
    'WELL_ROOM': Tile(2015, 4711, 1),
    'WELL_OF_VOYAGE': Tile(2009, 4711, 1),
    'VOYAGE_TEMPLE': Tile(2343, 9622, 0),
    'VOYAGE_EXIT': Tile(2313, 9623, 0),
    'ISAFDAR_ENTRY': Tile(2312, 3216, 0),
    'VOYAGE_ENTRANCE': Tile(2314, 3215, 0),
    'IORWERTH': Tile(2205, 3252, 0),
    'LOOM': Tile(2199, 3249, 0),
    'BARREL_SPAWN': Tile(2205, 3257, 0),
    'POT_SPAWN': Tile(2199, 3257, 0),
    'TRACKER': Tile(2257, 3149, 0),
    'FOOTPRINTS': Tile(2240, 3151, 0),
    'TAR': Tile(2263, 3128, 0),
    'SULPHUR': Tile(2256, 3127, 0),
    'OLD_CAMP_WEST': Tile(2231, 3149, 0),
    'CATAPULT': Tile(2185, 3182, 0),
    'LAZY_GUARD': Tile(2181, 3184, 0),
    'CAMP_ENTRANCE': Tile(2188, 3171, 0),
    'CAMP_INSIDE': Tile(2188, 3168, 0),
    'TYRAS_CAMP': Tile(2188, 3162, 0),
    'FURNACE': Tile(2193, 3147, 0),
    'QUARTERMASTER': Tile(2190, 3155, 0),
    'QUARRY': Tile(2323, 3269, 0),
    'RABBITS': Tile(2230, 3238, 0),
    'ARANDAR_SOUTH': Tile(2384, 3331, 0),
    'ARANDAR_NORTH': Tile(2384, 3337, 0),
    'STILL': Tile(2927, 3211, 0),
    'CHEMIST': Tile(2934, 3210, 0),
})
# Why: the pitfalls drop you into mapsquare 36_150 alongside the voyage temple, so z tells them apart: the temple sits at 9620-9635 and every spike pit below it at 9640-9660.
VOYAGE_MAX_Z = 9635


def regicide_area(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    if x >= 2304 and x <= 2367 and z >= 9600 and z <= 9663:
        return ('voyage' if z <= VOYAGE_MAX_Z else 'pit')
    if z >= 4500:
        return 'pass'
    # Why: Tirannwn is everything west and south of the Arandar palisade, the only join to the rest of the map, so the box is the 2 mapsquare columns the forest occupies plus the Arandar pass.
    if level == 0 and x >= 2160 and x <= 2390 and z >= 3110 and z <= 3334:
        return 'tirannwn'
    return 'mainland'


def held(snap, item):
    _v1 = (snap.inv_ids.get(item.id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, item):
    _v2 = (snap.bank_ids.get(item.id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def worn(snap, item):
    _v3 = ((item.id in snap.worn_ids) if snap.worn_ids is not None else None)
    return (_v3 if _v3 is not None else False)


def carried(snap, item):
    return held(snap, item) + ((1 if worn(snap, item) else 0))


def owned(snap, item):
    return held(snap, item) + banked(snap, item)


def count_held(snap, items):
    """How many of a set the pack holds; the 2 half-mixes share a display name."""
    return len([item for item in items if held(snap, item) > 0])

