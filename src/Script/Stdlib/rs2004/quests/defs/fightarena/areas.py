"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fightarena/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['FA_NPC', 'FA_OBJ', 'FA_ITEM', 'FA_LOC', 'FA_TILE', 'FA_AREA', 'pocket_of']

FA_NPC = Record({
    'GUARD1': 253,
    'DRUNK_GUARD': 254,
    'KHAZARD': 258,
    'BARMAN': 259,
    'HENGRAD': 263,
    'LADY_SERVIL': 264,
    'JEREMY_CELL': 265,
    'JEREMY_ARENA': 266,
    'JUSTIN': 267,
    'BOUNCER': 269,
    'OGRE': 270,
    'SCORPION': 271,
})
FA_OBJ = Record({'HELMET': 74, 'ARMOUR': 75, 'KEYS': 76, 'BREW': 77})
FA_ITEM = Record({'HELMET': 'Khazard helmet', 'ARMOUR': 'Khazard armour', 'KEYS': 'Khazard cell keys', 'BREW': 'Khali brew'})
FA_LOC = Record({'CHEST': 'Chest', 'DOOR1': 81, 'DOOR2': 82, 'JEREMY_DOOR': 80})
FA_TILE = Record({
    'YANILLE_BANK': Tile(2612, 3092, 0),
    'LADY_SERVIL': Tile(2566, 3199, 0),
    'BARMAN': Tile(2566, 3140, 0),
    'CHEST_STAND': Tile(2613, 3190, 0),
    'DOOR1_OUTSIDE': Tile(2617, 3172, 0),
    'DOOR1_INSIDE': Tile(2617, 3171, 0),
    'DRUNK_GUARD': Tile(2615, 3141, 0),
    'JEREMY_DOOR_STAND': Tile(2617, 3168, 0),
    'DOOR2_OUTSIDE': Tile(2607, 3151, 0),
    'DOOR2_INSIDE': Tile(2605, 3152, 0),
    'ARENA_CENTRE': Tile(2597, 3160, 0),
})
# Why: these are the bounding boxes of 4 floods over the baked collision pack with the scripted doors removed, and neither cell rect holds a building tile.
FA_AREA = Record({
    'JEREMY_CELL': Record({'min_x': 2614, 'max_x': 2616, 'min_z': 3166, 'max_z': 3170}),
    'PRISON_CELL': Record({'min_x': 2597, 'max_x': 2601, 'min_z': 3142, 'max_z': 3144}),
    'ARENA': Record({'min_x': 2583, 'max_x': 2606, 'min_z': 3152, 'max_z': 3170}),
    'BUILDING': Record({'min_x': 2585, 'max_x': 2619, 'min_z': 3139, 'max_z': 3171}),
})


def in_rect(tile, rect):
    return tile.x >= rect.min_x and tile.x <= rect.max_x and tile.z >= rect.min_z and tile.z <= rect.max_z


# Why: every crossing between these is a server teleport, so a step that assumes the wrong one sends the walker at a tile on the far side of a wall.
def pocket_of(tile):
    """Which sealed pocket a tile belongs to. Order matters: the cells sit inside the building's box."""
    if not tile or tile.level != 0:
        return 'outside'
    if in_rect(tile, FA_AREA.JEREMY_CELL):
        return 'jeremyCell'
    if in_rect(tile, FA_AREA.PRISON_CELL):
        return 'prisonCell'
    if in_rect(tile, FA_AREA.ARENA):
        return 'arena'
    if in_rect(tile, FA_AREA.BUILDING):
        return 'building'
    return 'outside'
