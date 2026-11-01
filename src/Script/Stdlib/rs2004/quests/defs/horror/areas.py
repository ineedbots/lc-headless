"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['HD_QUEST', 'HD_STAGE', 'HD_ID', 'HD_ITEM', 'HD_LOC', 'HD_TILE', 'SWORD_SHOP', 'ARCHERY_SHOP', 'RUNE_SHOP', 'GENERAL_SHOP', 'LARRISSA', 'GUNNJORN', 'JOSSIK']

HD_QUEST = 'Horror from the Deep'
HD_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'ENTERED_LIGHTHOUSE': 2,
    'FIXING_LIGHTHOUSE': 3,
    'REPAIRED_LIGHTHOUSE': 4,
    'DEFEATED_DAGJR': 5,
    'COMPLETE': 10,
})
HD_ID = Record({
    'KEY': 3848,
    'CASKET': 3849,
    'PLANK': 960,
    'NAILS': 1539,
    'HAMMER': 2347,
    'SWAMP_TAR': 1939,
    'MOLTEN_GLASS': 1775,
    'TINDERBOX': 590,
    'BARCRAWL_CARD': 455,
    'AIR_RUNE': 556,
    'WATER_RUNE': 555,
    'EARTH_RUNE': 557,
    'FIRE_RUNE': 554,
    'CHAOS_RUNE': 562,
    'DEATH_RUNE': 560,
    'LAW_RUNE': 563,
    'DAGGER': 1205,
    'ARROW': 882,
    'BUCKET': 1925,
    'BUCKET_OF_SAND': 1783,
    'SODA_ASH': 1781,
    'SEAWEED': 401,
    'STEEL_BAR': 2353,
    'COINS': 995,
})
HD_ITEM = Record({
    'KEY': 'Lighthouse key',
    'CASKET': 'Rusty casket',
    'PLANK': 'Plank',
    'NAILS': 'Nails',
    'HAMMER': 'Hammer',
    'SWAMP_TAR': 'Swamp tar',
    'MOLTEN_GLASS': 'Molten glass',
    'TINDERBOX': 'Tinderbox',
    'BARCRAWL_CARD': 'Barcrawl card',
    'AIR_RUNE': 'Air rune',
    'WATER_RUNE': 'Water rune',
    'EARTH_RUNE': 'Earth rune',
    'FIRE_RUNE': 'Fire rune',
    'CHAOS_RUNE': 'Chaos rune',
    'DEATH_RUNE': 'Death rune',
    'LAW_RUNE': 'Law rune',
    'DAGGER': 'Bronze dagger',
    'ARROW': 'Bronze arrow',
    'BUCKET': 'Bucket',
    'BUCKET_OF_SAND': 'Bucket of sand',
    'SODA_ASH': 'Soda ash',
    'SEAWEED': 'Seaweed',
    'COINS': 'Coins',
})
HD_LOC = Record({
    'BASALT': 'Basalt rock',
    'BRIDGE': 'Broken bridge',
    'PIPE': 'Obstacle pipe',
    'DOORWAY': 'Doorway',
    'STAIRS': 'Staircase',
    'LADDER': 'Iron ladder',
    'BOOKCASE': 'Bookcase',
    'LIGHT': 'Lighting mechanism',
    'WALL': 'Strange wall',
    'SAND_PIT': 'Sand pit',
    'RANGE': 'Range',
    'FURNACE': 'Furnace',
})
# Why: during the quest the lighthouse interior is the broken copy in mapsquare 38_71; repairing the light teleports you (+64,-960) into the live one in 39_56.
# Why: the doorway and stairs teleport, so nothing walks between them and every staircase from the live one routes back into the copy.
HD_TILE = Record({
    'CAUSEWAY_SOUTH': Tile(2522, 3594, 0),
    'LARRISSA': Tile(2508, 3635, 0),
    'LIGHTHOUSE_DOOR': Tile(2509, 3635, 0),
    'BRIDGE_WEST': Tile(2596, 3608, 0),
    'BRIDGE_EAST': Tile(2598, 3608, 0),
    'QUEST_LIGHTHOUSE_L0': Tile(2445, 4597, 0),
    'QUEST_STAIRS_BASE': Tile(2443, 4600, 0),
    'QUEST_LADDER': Tile(2444, 4603, 0),
    'QUEST_STAIRS_L1': Tile(2441, 4601, 1),
    'QUEST_BOOKCASE': Tile(2444, 4603, 1),
    'QUEST_STAIRS_L2': Tile(2441, 4601, 2),
    'QUEST_LIGHT': Tile(2443, 4598, 2),
    'REAL_STAIRS_L2': Tile(2506, 3640, 2),
    'REAL_LIGHTHOUSE_L0': Tile(2509, 3637, 0),
    'BASEMENT_LADDER': Tile(2519, 4619, 1),
    'WALL_SOUTH': Tile(2515, 4626, 1),
    'WALL_NORTH': Tile(2515, 4628, 1),
    'BASEMENT_DOWN': Tile(2515, 4629, 1),
    'CAVERN_LANDING': Tile(2515, 4633, 0),
    'JOSSIK': Tile(2518, 4634, 0),
    'POSTQUEST_CAVERN': Tile(2515, 10001, 1),
    'POSTQUEST_LADDER': Tile(2519, 9995, 1),
    'OUTPOST_PIPE_NORTH': Tile(2552, 3561, 0),
    'OUTPOST_PIPE_SOUTH': Tile(2552, 3558, 0),
    'GUNNJORN': Tile(2540, 3548, 0),
    'PLANK_SPAWNS': [Tile(2552, 3574, 0), Tile(2553, 3575, 0), Tile(2554, 3574, 0), Tile(2556, 3573, 0)],
    'SWAMP_TAR': Tile(3173, 3178, 0),
    'SEAWEED': Tile(2708, 3728, 0),
    'SAND_PIT': Tile(2541, 3103, 0),
    'YANILLE_RANGE': Tile(2550, 3099, 0),
    'FURNACE': Tile(2600, 3310, 0),
    'VARROCK_SWORDSHOP': Tile(3203, 3395, 0),
    'VARROCK_ARCHERY': Tile(3232, 3424, 0),
    'VARROCK_RUNES': Tile(3253, 3401, 0),
    'VARROCK_GENERAL': Tile(3218, 3415, 0),
})
SWORD_SHOP = Record({'npc': 'Shop keeper', 'anchor': HD_TILE.VARROCK_SWORDSHOP})
ARCHERY_SHOP = Record({'npc': 'Lowe', 'anchor': HD_TILE.VARROCK_ARCHERY})
RUNE_SHOP = Record({'npc': 'Aubury', 'anchor': HD_TILE.VARROCK_RUNES})
GENERAL_SHOP = Record({'npc': 'Shop keeper', 'anchor': HD_TILE.VARROCK_GENERAL})
LARRISSA = NpcStop('Larrissa', HD_TILE.LARRISSA, 8, [
    'With what?',
    'But how can I help?',
    "Okay, I'll help!",
    "I'll see what I can do",
    'How can I fix the bridge?',
    'Where is your cousin?',
])
GUNNJORN = NpcStop('Gunnjorn', HD_TILE.GUNNJORN, 8, [])
JOSSIK = NpcStop('Jossik', HD_TILE.JOSSIK, 8, [])
