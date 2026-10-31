"""Ported from rs2b0t's src/bot/api/ai/quests/defs/observatory/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import CATHERBY_RANGE
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['OBS_QUEST', 'OBS_STAGE', 'OBS_ID', 'OBS_ITEM', 'PLANKS_NEEDED', 'OBS_LOC', 'OBS_LOC_NAME', 'OBS_TILE', 'PROFESSOR', 'PROFESSOR_DOME', 'OBSERVATORY_TOOLS']

OBS_QUEST = 'Observatory Quest'
OBS_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'GIVEN_PLANKS': 2,
    'GIVEN_BRONZE': 3,
    'GIVEN_GLASS': 4,
    'GIVEN_MOULD': 5,
    'SENT_TELESCOPE': 6,
    'COMPLETE': 7,
})
OBS_ID = Record({
    'PLANK': 960,
    'BRONZE_BAR': 2349,
    'MOLTEN_GLASS': 1775,
    'LENS_MOULD': 602,
    'LENS': 603,
    'KEEP_KEY': 601,
    'SEAWEED': 401,
    'SODA_ASH': 1781,
    'BUCKET_OF_SAND': 1783,
    'COPPER_ORE': 436,
    'TIN_ORE': 438,
    'BRONZE_PICKAXE': 1265,
    'COINS': 995,
})
OBS_ITEM = Record({
    'PLANK': 'Plank',
    'BRONZE_BAR': 'Bronze bar',
    'MOLTEN_GLASS': 'Molten glass',
    'LENS_MOULD': 'Lens mould',
    'LENS': 'Lens',
    'KEEP_KEY': 'Keep key',
    'SEAWEED': 'Seaweed',
    'SODA_ASH': 'Soda ash',
    'BUCKET_OF_SAND': 'Bucket of sand',
    'COPPER_ORE': 'Copper ore',
    'TIN_ORE': 'Tin ore',
    'BRONZE_PICKAXE': 'Bronze pickaxe',
})
PLANKS_NEEDED = 3
# Why: 8 of the cavern's locs render "Chest" and 6 of them are `shutdungeonchest`, which spawns a poisonous spider on Search, so every lookup down here is by id.
OBS_LOC = Record({
    'RECEPTION_LADDER': 2187,
    'KEY_CHEST_SHUT': 2197,
    'KEY_CHEST_OPEN': 2198,
    'GATE_RIGHT': 2199,
    'GATE_LEFT': 2200,
    'SACK': 2212,
    'TELESCOPE': 2210,
})
OBS_LOC_NAME = Record({
    'LADDER': 'Ladder',
    'CHEST': 'Chest',
    'GATE': 'Keep gate',
    'SACK': 'Sack',
    'TELESCOPE': 'Telescope',
    'RANGE': 'Range',
    'FURNACE': 'Furnace',
})
# Why: the reception, the cavern and the dome are 3 pockets of one map; the dome is walled off from the surface, so its only door is the cavern below.
OBS_TILE = Record({
    'PROFESSOR': Tile(2438, 3186, 0),
    'RECEPTION_LADDER': Tile(2444, 3192, 0),
    'DUNGEON_LANDING': Tile(2420, 9459, 0),
    'KEY_CHEST_STAND': Tile(2428, 9418, 0),
    'GATE_NORTH': Tile(2390, 9458, 0),
    'GATE_SOUTH': Tile(2390, 9457, 0),
    'SACK_STAND': Tile(2390, 9454, 0),
    'DOME_LADDER_FOOT': Tile(2423, 9440, 0),
    'DOME_ARRIVE': Tile(2440, 3165, 0),
    'TELESCOPE_STAND': Tile(2440, 3159, 0),
    'SAND_SPAWN': Tile(2461, 3178, 0),
    'PLANK_SPAWNS': [Tile(2552, 3574, 0), Tile(2553, 3575, 0), Tile(2554, 3574, 0), Tile(2556, 3573, 0)],
    'SEAWEED_SPAWN': Tile(2708, 3728, 0),
    'MINE': Tile(2631, 3146, 0),
    'FURNACE': Tile(2600, 3310, 0),
    'RANGE_LOC': CATHERBY_RANGE.loc,
    'RANGE_STAND': CATHERBY_RANGE.stand,
    'BANK': Tile(2655, 3283, 0),
})
PROFESSOR = NpcStop('Observatory professor', OBS_TILE.PROFESSOR, 6, ["I'd like to have a look through that telescope.", 'Sounds interesting, what can I do for you?'])
PROFESSOR_DOME = 'Observatory professor'
OBSERVATORY_TOOLS = [
    'coins',
    'plank',
    'bronze bar',
    'molten glass',
    'lens mould',
    'lens',
    'keep key',
    'seaweed',
    'soda ash',
    'bucket of sand',
    'copper ore',
    'tin ore',
    'pickaxe',
]
