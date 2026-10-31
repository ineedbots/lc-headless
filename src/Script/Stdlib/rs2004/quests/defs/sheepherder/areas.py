"""Ported from rs2b0t's src/bot/api/ai/quests/defs/sheepherder/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['SHEEP', 'ORDINAL', 'BONES_OBJ', 'PROD_OBJ', 'FEED_OBJ', 'JACKET_OBJ', 'TROUSERS_OBJ', 'FURNACE_LOC', 'GATE_LOC', 'PROD', 'FEED', 'JACKET', 'TROUSERS', 'sheep_name', 'HALGRIVE', 'ORBON', 'SHEEP_SPAWN', 'BANK', 'GATE_OUTSIDE', 'GATE_INSIDE', 'FURNACE_STAND', 'PROD_SPAWN', 'PEN', 'GATE_ZONE', 'in_box']

SHEEP = [1, 2, 3, 4]
ORDINAL = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth'}
# Why: all 4 sets of remains render "Bones", as does the ordinary drop, so every lookup is by id.
BONES_OBJ = {1: 280, 2: 281, 3: 282, 4: 283}
PROD_OBJ = 278
FEED_OBJ = 279
JACKET_OBJ = 284
TROUSERS_OBJ = 285
FURNACE_LOC = 165
GATE_LOC = [166, 167]
PROD = 'Prod'
FEED = 'Feed'
JACKET = 'Plague jacket'
TROUSERS = 'Plague trousers'


def sheep_name(n):
    return f'Diseased sheep {n}'


HALGRIVE = NpcStop('Councillor Halgrive', Tile(2617, 3299, 0), 8, ["What's wrong?", 'I can do that for you.'])
ORBON = NpcStop('Doctor Orbon', Tile(2614, 3306, 0), 8, ["Ok, I'll take it."])
# Why: an npc only enters the client's list within about 15 tiles, so a sheep 2 fields away isn't missing; the leg walks to its map spawn before looking.
SHEEP_SPAWN = {1: Tile(2610, 3344, 0), 2: Tile(2622, 3367, 0), 3: Tile(2561, 3389, 0), 4: Tile(2611, 3391, 0)}
BANK = Tile(2616, 3332, 0)
GATE_OUTSIDE = Tile(2594, 3361, 0)
GATE_INSIDE = Tile(2595, 3361, 0)
FURNACE_STAND = Tile(2604, 3361, 0)
PROD_SPAWN = Tile(2604, 3357, 0)
PEN = Record({'x0': 2595, 'x1': 2609, 'z0': 3351, 'z1': 3364})
GATE_ZONE = Record({'x0': 2592, 'x1': 2594, 'z0': 3360, 'z1': 3363})


def in_box(box, t):
    return t is not None and t.level == 0 and t.x >= box.x0 and t.x <= box.x1 and t.z >= box.z0 and t.z <= box.z1
