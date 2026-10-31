"""Ported from rs2b0t's src/bot/api/ai/quests/defs/plaguecity/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['PC_ITEM', 'PC_NPC', 'PC_LOC', 'PC_TILE', 'plague_area', 'held', 'banked', 'owned', 'worn']

# Why: 4 of these display as "Door", 2 as "Stairs" and 2 as "Bucket", so every lookup that can collide goes through the id.
PC_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'SPADE': Record({'id': 952, 'name': 'Spade'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'BUCKET': Record({'id': 1925, 'name': 'Bucket'}),
    'BUCKET_WATER': Record({'id': 1929, 'name': 'Bucket of water'}),
    'BUCKET_MILK': Record({'id': 1927, 'name': 'Bucket of milk'}),
    'CHOCOLATE_BAR': Record({'id': 1973, 'name': 'Chocolate bar'}),
    'CHOCOLATE_DUST': Record({'id': 1975, 'name': 'Chocolate dust'}),
    'CHOCOLATY_MILK': Record({'id': 1977, 'name': 'Chocolaty milk'}),
    'PESTLE': Record({'id': 233, 'name': 'Pestle and mortar'}),
    'SNAPE_GRASS': Record({'id': 231, 'name': 'Snape grass'}),
    'DWELLBERRIES': Record({'id': 2126, 'name': 'Dwellberries'}),
    'GAS_MASK': Record({'id': 1506, 'name': 'Gas mask'}),
    'PICTURE': Record({'id': 1510, 'name': 'Picture'}),
    'TURNIP_BOOK': Record({'id': 1509, 'name': 'Book'}),
    'SCRUFFY_NOTE': Record({'id': 1508, 'name': 'A scruffy note'}),
    'HANGOVER_CURE': Record({'id': 1504, 'name': 'Hangover cure'}),
    'WARRANT': Record({'id': 1503, 'name': 'Warrant'}),
    'ELENA_KEY': Record({'id': 1507, 'name': 'A small key'}),
    'ARDOUGNE_SCROLL': Record({'id': 1505, 'name': 'A magic scroll'}),
})
PC_NPC = Record({
    'EDMOND': 'Edmond',
    'ALRENA': 'Alrena',
    'JETHICK': 'Jethick',
    'TED': 'Ted Rehnison',
    'MARTHA': 'Martha Rehnison',
    'MILLI': 'Milli Rehnison',
    'CLERK': 'Clerk',
    'BRAVEK': 'Bravek',
    'ELENA': 'Elena',
    'MOURNER': 'Mourner',
})
PC_LOC = Record({
    'MUD_PATCH': [2531, 2532],
    'MUD_PILE': 2533,
    'SEWER_PIPE': 2541,
    'MANHOLE_SHUT': 2543,
    'MANHOLE_OPEN': 2544,
    'CUPBOARD_SHUT': 2524,
    'CUPBOARD_OPEN': 2525,
    'REHNISON_DOOR': 2537,
    'REHNISON_STAIRS_UP': 2539,
    'REHNISON_STAIRS_DOWN': 2540,
    'PLAGUE_DOOR': 2535,
    'BARREL': 2530,
    'HOUSE_STAIRS_DOWN': 2522,
    'HOUSE_STAIRS_UP': 2523,
    'ELENA_GATE': 2526,
    'BRAVEK_DOOR': 2528,
})
PC_TILE = Record({
    'BANK': Tile(2616, 3332, 0),
    'EDMOND': Tile(2568, 3334, 0),
    'ALRENA': Tile(2573, 3333, 0),
    'HOUSE_FLOOR': Tile(2575, 3333, 0),
    'CUPBOARD': Tile(2575, 3334, 0),
    'GARDEN': Tile(2566, 3330, 0),
    'FOUNTAIN': Tile(2629, 3311, 0),
    'BUCKET_SPAWN': Tile(2616, 3255, 0),
    'COW_FIELD': Tile(2664, 3346, 0),
    'AEMAD': Tile(2613, 3294, 0),
    'DWELLBERRIES': Tile(2645, 3498, 0),
    'SNAPE_GRASS': Tile(2906, 3297, 0),
    'JATIX': Tile(2899, 3427, 0),
    'WYDIN': Tile(3014, 3204, 0),
    'SEWER_LANDING': Tile(2562, 9737, 0),
    'MUD_PILE': Tile(2561, 9737, 0),
    'SEWER_EDMOND': Tile(2535, 9719, 0),
    'SEWER_PIPE': Tile(2530, 9703, 0),
    'WEST_LANDING': Tile(2529, 3304, 0),
    'MANHOLE': Tile(2529, 3303, 0),
    'JETHICK': Tile(2540, 3305, 0),
    'REHNISON_DOOR': Tile(2532, 3327, 0),
    'REHNISON_TED': Tile(2532, 3331, 0),
    'REHNISON_STAIRS': Tile(2528, 3332, 0),
    'REHNISON_TOP': Tile(2527, 3331, 1),
    'MILLI': Tile(2530, 3331, 1),
    'PLAGUE_DOOR': Tile(2533, 3272, 0),
    'PLAGUE_DOOR_INSIDE': Tile(2533, 3271, 0),
    'CLERK': Tile(2529, 3317, 0),
    'BRAVEK_DOOR': Tile(2529, 3314, 0),
    'BRAVEK': Tile(2535, 3314, 0),
    'BARREL': Tile(2535, 3269, 0),
    'HOUSE_STAIRS_DOWN': Tile(2535, 3270, 0),
    'HOUSE_STAIRS_UP': Tile(2537, 9671, 0),
    'ELENA_GATE': Tile(2538, 9672, 0),
    'ELENA': Tile(2540, 9672, 0),
})


def plague_area(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    if x >= 2528 and x <= 2548 and z >= 9655 and z <= 9688:
        return 'cellar'
    if x >= 2490 and x <= 2600 and z >= 9690 and z <= 9770:
        return 'sewer'
    if level == 1 and x >= 2520 and x <= 2540 and z >= 3322 and z <= 3340:
        return 'upstairs'
    if level == 0 and x >= 2433 and x <= 2556 and z >= 3266 and z <= 3334:
        return 'west'
    return ('east' if level == 0 else 'unknown')


def held(snap, item):
    _v1 = (snap.inv_ids.get(item.id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, item):
    _v2 = (snap.bank_ids.get(item.id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def owned(snap, item):
    return held(snap, item) + banked(snap, item)


def worn(snap, item):
    _v3 = ((item.id in snap.worn_ids) if snap.worn_ids is not None else None)
    return (_v3 if _v3 is not None else False)
