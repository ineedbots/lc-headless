"""Ported from rs2b0t's src/bot/api/ai/quests/defs/treegnome/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['TG_ITEM', 'TG_NPC', 'TG_LOC', 'TG_TILE', 'LOGS_WANTED', 'in_khazard_hall', 'in_ladder_room', 'in_chest_floor', 'in_stronghold', 'held', 'banked', 'owned']

# Why: `orb_of_protection` and `orbs_of_protection` both display "Orb of protection", and only the plural finishes the quest.
# Why: 3 objs display "Logs", and `commander_montai` deletes obj 1511 alone.
TG_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'LOGS': Record({'id': 1511, 'name': 'Logs'}),
    'ORB': Record({'id': 587, 'name': 'Orb of protection'}),
    'ORBS': Record({'id': 588, 'name': 'Orb of protection'}),
    'AMULET': Record({'id': 589, 'name': 'Gnome amulet'}),
})
TG_NPC = Record({
    'BOLREN': 'King Bolren',
    'MONTAI': 'Commander Montai',
    'ELKOY': 'Elkoy',
    'WARLORD': 'Khazard warlord',
    'COMMANDER': 'Khazard commander',
    'AEMAD': 'Aemad',
})
TG_LOC = Record({
    'BALLISTA': 2181,
    'CHEST_SHUT': 2183,
    'CHEST_OPEN': 2182,
    'FRONT_DOOR': 2184,
    'CRUMBLED_WALL': 2185,
    'INNER_DOOR': 1530,
    'LADDER_UP': 1747,
    'LADDER_DOWN': 1746,
})
TG_TILE = Record({
    'BANK': Tile(2655, 3283, 0),
    'BOLREN': Tile(2542, 3170, 0),
    'MONTAI': Tile(2523, 3211, 0),
    'TREES': Tile(2521, 3201, 0),
    'AXE_SHOP': Tile(2613, 3294, 0),
    'BALLISTA_STAND': Tile(2511, 3211, 0),
    'WALL_STAND': Tile(2509, 3252, 0),
    'HALL_LANDING': Tile(2509, 3255, 0),
    'INNER_DOOR_STAND': Tile(2506, 3256, 0),
    'LADDER_STAND': Tile(2503, 3253, 0),
    'CHEST_STAND': Tile(2506, 3258, 1),
    'FRONT_DOOR_STAND': Tile(2502, 3251, 0),
    'OUTSIDE_FRONT_DOOR': Tile(2502, 3250, 0),
    'WARLORD': Tile(2457, 3302, 0),
})
LOGS_WANTED = 6
# Why: The east hall and west ladder room overlap in x/z bounds, so classify them separately.
HALL_ROWS = {
    3254: [2508, 2511],
    3255: [2507, 2512],
    3256: [2506, 2512],
    3257: [2500, 2511],
    3258: [2502, 2512],
    3259: [2503, 2511],
}
LADDER_ROOM_ROWS = {
    3251: [2501, 2503],
    3252: [2500, 2504],
    3253: [2500, 2505],
    3254: [2500, 2506],
    3255: [2500, 2506],
    3256: [2500, 2504],
}


def in_rows(tile, rows):
    span = rows.get(tile.z)
    return tile.level == 0 and span is not None and tile.x >= span[0] and tile.x <= span[1]


def in_khazard_hall(tile):
    """The hall behind the crumbled wall: the only way on is the inner door."""
    return tile is not None and in_rows(tile, HALL_ROWS)


def in_ladder_room(tile):
    """The west room, which holds the ladder up and the front door out."""
    return tile is not None and in_rows(tile, LADDER_ROOM_ROWS)


def in_chest_floor(tile):
    """The stronghold's first floor, where the chest is."""
    return tile is not None and tile.level == 1 and tile.x >= 2499 and tile.x <= 2507 and tile.z >= 3250 and tile.z <= 3260


def in_stronghold(tile):
    return in_khazard_hall(tile) or in_ladder_room(tile) or in_chest_floor(tile)


def held(snap, item):
    _v1 = snap.inv_ids.get(item.id)
    return (_v1 if _v1 is not None else 0)


def banked(snap, item):
    _v2 = snap.bank_ids.get(item.id)
    return (_v2 if _v2 is not None else 0)


def owned(snap, item):
    return held(snap, item) + banked(snap, item)
