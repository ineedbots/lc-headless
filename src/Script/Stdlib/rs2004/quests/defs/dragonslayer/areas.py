"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dragonslayer/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.geometry import Tile

__all__ = ['DS_NPC', 'DS_LOC', 'DS_ID', 'DS_ITEM', 'SHIP_REPAIR', 'WORMBRAIN_PRICE', 'SHIP_PRICE']

DS_NPC = Record({
    'GUILDMASTER': Tile(3191, 3362, 0),
    'OZIACH': Tile(3069, 3517, 0),
    'DUKE': Tile(3212, 3220, 1),
    'ORACLE': Tile(3015, 3504, 0),
    'WORMBRAIN': Tile(3014, 3186, 0),
    'WORMBRAIN_STAND': Tile(3012, 3186, 0),
    'KLARENSE': Tile(3047, 3204, 0),
    'NED': Tile(3100, 3258, 0),
    'MELZAR': Tile(2929, 9649, 0),
    'ELVARG': Tile(2852, 9637, 0),
    'NED_ABOARD': Tile(3046, 9640, 3),
})
DS_LOC = Record({
    'MAZE_DOOR': Tile(2941, 3248, 0),
    'MAZE_LADDER_DOWN': Tile(2932, 3240, 0),
    'RED_DOORS': [Tile(2926, 3244, 0), Tile(2926, 3248, 0), Tile(2926, 3253, 0)],
    'ORANGE_DOORS': [Tile(2931, 3247, 1), Tile(2931, 3250, 1), Tile(2931, 3253, 1), Tile(2931, 3256, 1)],
    'YELLOW_DOORS': [Tile(2924, 3249, 2), Tile(2928, 3249, 2), Tile(2931, 3249, 2), Tile(2936, 3256, 2)],
    'BLUE_DOOR': Tile(2931, 9643, 0),
    'MAGENTA_DOOR': Tile(2929, 9652, 0),
    'GREEN_DOOR': Tile(2936, 9655, 0),
    'MAZE_CHEST': Tile(2935, 9657, 0),
    'ORACLE_DOOR': Tile(3051, 9840, 0),
    'ORACLE_DOOR_STAND': Tile(3050, 9840, 0),
    'ORACLE_CHEST': Tile(3057, 9841, 0),
    'ORACLE_CHEST_STAND': Tile(3057, 9842, 0),
    'GANGPLANK': Tile(3047, 3205, 1),
    'GANGPLANK_STAND': Tile(3047, 3204, 0),
    'SHIP_LADDER': Tile(3049, 3208, 1),
    'SHIP_HOLE': Tile(3047, 9639, 1),
    'CRANDOR_ROCK': Tile(2833, 3255, 0),
    'CRANDOR_SECRET_DOOR': Tile(2836, 9600, 0),
    'SECRET_WALL_KARAMJA_STAND': Tile(2836, 9599, 0),
    'ELVARG_GATE': Tile(2847, 9636, 0),
    'ELVARG_GATE_STAND': Tile(2846, 9637, 0),
    'ELVARG_GATE_INSIDE': Tile(2847, 9637, 0),
})
DS_ID = Record({
    'MAP_MELZAR': 1535,
    'MAP_WORMBRAIN': 1536,
    'MAP_ORACLE': 1537,
    'MAP': 1538,
    'NAILS': 1539,
    'SHIELD': 1540,
    'MAZE_KEY': 1542,
    'RED_KEY': 1543,
    'ORANGE_KEY': 1544,
    'YELLOW_KEY': 1545,
    'BLUE_KEY': 1546,
    'MAGENTA_KEY': 1547,
    'GREEN_KEY': 1548,
    'PLANK': 960,
    'HAMMER': 2347,
    'MIND_BOMB': 1907,
    'UNFIRED_BOWL': 1791,
    'LOBSTER_POT': 301,
    'SILK': 950,
})
DS_ITEM = Record({
    'MAZE_KEY': 'Maze key',
    'KEY': 'Key',
    'MAP_PART': 'Map part',
    'MAP': 'Crandor map',
    'NAILS': 'Nails',
    'PLANK': 'Plank',
    'HAMMER': 'Hammer',
    'SHIELD': 'Dragonfire shield',
    'MIND_BOMB': "Wizard's mind bomb",
    'UNFIRED_BOWL': 'Unfired bowl',
    'LOBSTER_POT': 'Lobster pot',
    'SILK': 'Silk',
})
SHIP_REPAIR = Record({'planks': 3, 'nails_per_plank': 4})
WORMBRAIN_PRICE = 10000
SHIP_PRICE = 2000
