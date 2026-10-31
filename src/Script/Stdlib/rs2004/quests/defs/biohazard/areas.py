"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['BIO_ITEM', 'VIALS', 'BIO_NPC', 'BIO_LOC', 'SICK_MOURNER_ID', 'BIO_TILE', 'PIGEON_ZONE', 'bio_area', 'in_guidor_quarter', 'in_pigeon_zone', 'held', 'banked', 'worn', 'owned']

# Why: both priest halves render "Priest gown", both cages render "Pigeon cage" and the mourner key renders "Key", so every lookup in this quest goes through the object id.
BIO_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'ETHENEA': Record({'id': 415, 'name': 'Ethanea'}),
    'LIQUID_HONEY': Record({'id': 416, 'name': 'Liquid honey'}),
    'SULPHURIC_BROLINE': Record({'id': 417, 'name': 'Sulphuric broline'}),
    'PLAGUE_SAMPLE': Record({'id': 418, 'name': 'Plague sample'}),
    'TOUCH_PAPER': Record({'id': 419, 'name': 'Touch paper'}),
    'DISTILLATOR': Record({'id': 420, 'name': 'Distillator'}),
    'BIRDFEED': Record({'id': 422, 'name': 'Bird feed'}),
    'MOURNER_KEY': Record({'id': 423, 'name': 'Key'}),
    'PIGEONS': Record({'id': 424, 'name': 'Pigeon cage'}),
    'EMPTY_CAGE': Record({'id': 425, 'name': 'Pigeon cage'}),
    'PRIEST_GOWN': Record({'id': 426, 'name': 'Priest gown'}),
    'PRIEST_ROBE': Record({'id': 428, 'name': 'Priest gown'}),
    'DOCTOR_GOWN': Record({'id': 430, 'name': "Doctors' gown"}),
    'ROTTEN_APPLES': Record({'id': 1984, 'name': 'Rotten apples'}),
})
VIALS = [BIO_ITEM.SULPHURIC_BROLINE, BIO_ITEM.ETHENEA, BIO_ITEM.LIQUID_HONEY]
BIO_NPC = Record({
    'ELENA': 'Elena',
    'JERICO': 'Jerico',
    'OMART': 'Omart',
    'KILRON': 'Kilron',
    'MOURNER': 'Mourner',
    'CHEMIST': 'Chemist',
    'HOPS': 'Hops',
    'DEVINCI': 'DeVinci',
    'CHANCY': 'Chancy',
    'THESSALIA': 'Thessalia',
    'GUIDOR': 'Guidor',
    'LATHAS': 'King Lathas',
})
BIO_LOC = Record({
    'JERICO_CUPBOARD_SHUT': 2056,
    'JERICO_CUPBOARD_OPEN': 2057,
    'WATCHTOWER': 2067,
    'CAULDRON': 2043,
    'NURSE_CUPBOARD_SHUT': 2062,
    'NURSE_CUPBOARD_OPEN': 2063,
    'HQ_DOOR': 2036,
    'HQ_CRATE': 2064,
    'GUIDOR_DOOR': 2032,
    'VARROCK_GATE': [2050, 2051],
})
# Why: `mournerstew2` upstairs shares its display name with every other Mourner in the city, and only that one drops the key.
SICK_MOURNER_ID = 370
BIO_TILE = Record({
    'ARDOUGNE_BANK': Tile(2616, 3332, 0),
    'ELENA': Tile(2592, 3336, 0),
    'JERICO': Tile(2612, 3324, 0),
    'JERICO_CUPBOARD': Tile(2611, 3325, 0),
    'PIGEON_SPAWN': Tile(2618, 3324, 0),
    'WATCHTOWER': Tile(2564, 3303, 0),
    'OMART': Tile(2559, 3266, 0),
    'KILRON': Tile(2556, 3266, 0),
    'LADDER_WEST': Tile(2556, 3267, 0),
    'LADDER_EAST': Tile(2559, 3267, 0),
    'ROTTEN_APPLES': Tile(2535, 3333, 0),
    'CAULDRON': Tile(2542, 3332, 0),
    'NURSE_CUPBOARD': Tile(2518, 3275, 0),
    'HQ_DOOR': Tile(2551, 3320, 0),
    'HQ_INSIDE': Tile(2551, 3321, 0),
    'HQ_UPSTAIRS': Tile(2550, 3326, 1),
    'HQ_CRATE': Tile(2554, 3326, 1),
    'LATHAS': Tile(2578, 3293, 1),
    'CHEMIST': Tile(2934, 3211, 0),
    'HOPS': Tile(2931, 3219, 0),
    'DEVINCI': Tile(2933, 3219, 0),
    'CHANCY': Tile(2935, 3219, 0),
    'THESSALIA': Tile(3204, 3417, 0),
    'GATE_OUTSIDE': Tile(3263, 3406, 0),
    'GATE_INSIDE': Tile(3265, 3406, 0),
    'DANCING_DONKEY': Tile(3270, 3390, 0),
    'GUIDOR_DOOR': Tile(3282, 3382, 0),
    'GUIDOR': Tile(3285, 3381, 0),
    'VARROCK_BANK': Tile(3253, 3420, 0),
    'SEWER_MUD_PILE': Tile(2561, 9737, 0),
    'MANHOLE': Tile(2529, 3303, 0),
})
# Why: `opheld1,pigeons` only releases them inside this box and the journal gives no second chance; outside it the cage says the pigeons do not want to leave.
PIGEON_ZONE = Record({'x0': 2559, 'x1': 2565, 'z0': 3299, 'z1': 3307})


# Why: `mournerstewdoor` is SCRIPT_REFUSED, so the headquarters and its first floor are a sealed pocket the navigator has no route into; every branch has to know which side we're on.
def bio_area(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    if x >= 2490 and x <= 2600 and z >= 9690 and z <= 9770:
        return 'sewer'
    if level == 1 and x >= 2540 and x <= 2557 and z >= 3320 and z <= 3330:
        return 'hqUpstairs'
    if level == 1 and x >= 2565 and x <= 2590 and z >= 3283 and z <= 3310:
        return 'castleUpstairs'
    if level == 0 and x >= 2542 and x <= 2555 and z >= 3321 and z <= 3327:
        return 'hq'
    if level == 0 and x >= 2433 and x <= 2556 and z >= 3266 and z <= 3334:
        return 'west'
    return ('mainland' if level == 0 else 'unknown')


# Why: the Varrock east gate searches both ways between given_distillator and found_secret, so the vials only travel inside this quarter, where Guidor and the inn both are.
def in_guidor_quarter(tile):
    if not tile or tile.level != 0:
        return False
    return tile.x >= 3264 and tile.x <= 3287 and tile.z >= 3376 and tile.z <= 3407


def in_pigeon_zone(tile):
    if not tile or tile.level != 0:
        return False
    return tile.x >= PIGEON_ZONE.x0 and tile.x <= PIGEON_ZONE.x1 and tile.z >= PIGEON_ZONE.z0 and tile.z <= PIGEON_ZONE.z1


def held(snap, item):
    _v1 = (snap.inv_ids.get(item.id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, item):
    _v2 = (snap.bank_ids.get(item.id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def worn(snap, item):
    _v3 = ((item.id in snap.worn_ids) if snap.worn_ids is not None else None)
    return (_v3 if _v3 is not None else False)


def owned(snap, item):
    """What `obj_gettotal` counts: pack plus bank plus what is worn."""
    return held(snap, item) + banked(snap, item) + ((1 if worn(snap, item) else 0))
